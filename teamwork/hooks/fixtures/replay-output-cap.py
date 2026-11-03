#!/usr/bin/env python3
"""Replay closed teamwork tasks in clean `claude -p` runs, with and without the output-cap arm's hook, judge each run by
its task's own `[check]`s, and keep one record per run in `output-cap-runs/`, from which alone every count and check reads.

usage: replay-output-cap.py --list-arms
usage: replay-output-cap.py --pick-tasks [--arms <arm>,<arm>] <pull request>...
usage: replay-output-cap.py --run <task> <arm> <repeat>
usage: replay-output-cap.py --run-all [--repeats <n>] [--max-dollars <x>] [--parallel <n>] [--arms <arm>,...] [--tasks <task>,...]
usage: replay-output-cap.py --count tasks|fewest-runs
usage: replay-output-cap.py --check-records|--check-clean|--check-firing|--check-spend|--check-models|--probe-arms
usage: replay-output-cap.py --probe-arm <arm>|--probe-allow <arm>|--check-measured <arm>
usage: replay-output-cap.py --check-plan <issue>
usage: replay-output-cap.py --check-landing
usage: replay-output-cap.py --reparse
usage: replay-output-cap.py --summary

`--pick-tasks` runs each `[check]` of each pull request's task, but those that reach GitHub, herdr, Claude or a path
outside the repository, at the merge commit's parent and at the merge commit, each in a fresh export, and adds to
`output-cap-tasks.json` each task with a check that fails at the parent and passes at the merge, every such check
kept as the run's judge. `--run` replays one task from its parent in a fresh export, judges it and writes its record;
`--run-all` runs each missing record of each task's own arms (`none` and `output-cap` for #1159's tasks, `none` and
`teamwork-cap` for those picked with `--arms none,teamwork-cap`), stopping before the chosen tasks' records would cost
more than `--max-dollars` (120). `teamwork-cap` runs the shipped `teamwork/hooks/cap-program-output.py`; `--probe-arm`
feeds it real Bash output, `--probe-allow` runs it once on Haiku under a `Bash(seq:*)` allow rule only, and
`--check-landing` prints `ok` when `teamwork/hooks/hooks.json` names it exactly when its gain on the new tasks holds.
A run's net saving is the cut tokens' carry to the run's end, less each later call that read a cut output's file: its
result's carry and its turn's cost; tokens are characters over 2.2, priced as measure-context-share.py prices them."""
import concurrent.futures
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import criteria_check  # noqa: E402
import issue_state  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
RECORDS = HERE / "output-cap-runs"
# raw streams stay outside the repository, being megabytes each, so a record can be re-read without a paid rerun
STREAMS = pathlib.Path(tempfile.gettempdir(), "replay-output-cap-streams")
TASKS = HERE / "output-cap-tasks.json"
ARMS = {"none": None, "output-cap": HERE / "output-cap-arm", "teamwork-cap": HERE / "teamwork-cap-arm"}
# the arm whose hook each arm runs, as the init event names its hook events
ARM_HOOKS = {"none": None, "output-cap": "PreToolUse:Bash", "teamwork-cap": "PostToolUse:Bash"}
SHIPPED_HOOK = ROOT / "teamwork" / "hooks" / "cap-program-output.py"
# #1159's tasks replay the test arm; any task picked later replays the shipped hook
FIRST_ARMS = ["none", "output-cap"]
NEW_ARMS = ["none", "teamwork-cap"]
NEW_LIMIT = 20.0
PLAN_ISSUE = 1172
REPO = "kalaluthien/mumu-claude-plugin"
MODEL, BUDGET, LIMIT = "sonnet", "5", 120.0
CHARS_PER_TOKEN = 2.2
WEIGHT = {"opus": 5.0, "sonnet": 3.0, "haiku": 1.0}
SWITCHES = {"CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}
CLEAN_FLAGS = [["--setting-sources", ""], ["--strict-mcp-config"], ["--max-budget-usd", BUDGET]]
BUILT_IN = re.compile(r"^cc-plugin-")
CUT = re.compile(r"\[output cap: (\d+) of (\d+) lines cut here; all of them are in (\S+);")
# the shipped hook's note also counts characters and may appear once per stream
SHIPPED_CUT = re.compile(r"\[output cap: (\d+) of (\d+) lines and (\d+) of (\d+) characters cut here; all of them are in (\S+); "
                         r"read a range of that file, not all of it\]")
# a check that reaches outside the export would judge the live machine, not the run
OUTSIDE = re.compile(r"\b(?:gh|herdr|claude|curl)\b|https?://|/Users/|~/|\$HOME|origin/")
BLOCKED_TOOLS = ("gh", "herdr", "claude")
# a later call naming a file the cut command read may be the model fetching the cut part again by another range
SOURCE_FILE = re.compile(r"[\w.-]+\.(?:py|md|json|jsonl|sh|txt|ya?ml|toml)\b")
REREAD_WINDOW = 2
FILE_READ = re.compile(r"\b(?:cat|sed|head|tail)\b")
# a command that sets its own EXIT trap or execs replaces the cap's trap, so its output would vanish
CAP_BREAKER = re.compile(r"\btrap\b|(?:^|[;&|]\s*)exec\b")
CHECK_TIMEOUT = 180
RUN_TIMEOUT = 3600
PROMPT = """You are replaying a past task in a fresh checkout of the mumu-claude-plugin repository, your working folder.
Do the task below fully: change the files so that each `[check]` of its Definition of done passes, run the checks you can,
then commit your change with git. GitHub, herdr and other Claude sessions are off in this replay: skip each step that reads
or writes an issue, pull request, comment or session (filing, commenting, judging, pushing, telling), and each check
that needs one.

Task #{number}: {title}

{body}"""


def gh_json(*args):
    return json.loads(subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout)


def export(sha, into):
    """A fresh repository at SHA's tree in INTO, one commit, so checks that read git see a clean tree."""
    into.mkdir(parents=True)
    archive = subprocess.run(["git", "-C", str(ROOT), "archive", sha], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(into)], input=archive, check=True)
    identity = {**os.environ, "GIT_AUTHOR_NAME": "replay", "GIT_AUTHOR_EMAIL": "replay@localhost",
                "GIT_COMMITTER_NAME": "replay", "GIT_COMMITTER_EMAIL": "replay@localhost"}
    for command in (["git", "init", "-q", "-b", "main"], ["git", "add", "-A"], ["git", "commit", "-q", "-m", f"base {sha}"]):
        subprocess.run(command, cwd=into, env=identity, check=True, capture_output=True)


def run_check(command, cwd):
    try:
        done = subprocess.run(["bash", "-c", command], cwd=cwd, capture_output=True, text=True, timeout=CHECK_TIMEOUT,
                              stdin=subprocess.DEVNULL)
        return done.returncode, (done.stdout + done.stderr).strip()
    except subprocess.TimeoutExpired:
        return None, f"timed out after {CHECK_TIMEOUT} s"


def verdict(test, status, out):
    kind, want = test
    if status is None:
        return "fail"
    if kind == "exits":
        return "pass" if status == want else "fail"
    if kind == "more":
        first = out.split(maxsplit=1)[:1]
        return "pass" if first and first[0].isdigit() and int(first[0]) >= want else "fail"
    return "pass" if out == want else "fail"


def task_checks(body):
    for index, line in enumerate(issue_state.ITEM.findall(issue_state.sections(body).get("done", "")), 1):
        _, kind, _, detail = issue_state.CRITERION.match(line).groups()
        if kind != "check":
            continue
        command, test = criteria_check.expectation(detail)
        if test[0] is not None and not OUTSIDE.search(command):
            yield {"index": index, "command": command, "test": list(test)}


def task_arms(entry):
    return entry.get("arms", FIRST_ARMS)


def task_list():
    return json.loads(TASKS.read_text()) if TASKS.exists() else []


def arms_of(task):
    return next((task_arms(entry) for entry in task_list() if entry["task"] == task), FIRST_ARMS)


def pick_tasks(numbers, arms):
    tasks = json.loads(TASKS.read_text()) if TASKS.exists() else []
    known = {task["task"] for task in tasks}
    for number in numbers:
        pull = gh_json("api", f"repos/{REPO}/pulls/{number}")
        found = re.findall(r"#(\d+)", pull.get("body") or "")
        merge = pull.get("merge_commit_sha")
        if not found or not merge:
            print(f"skip pull {number}: no task or no merge")
            continue
        issue = gh_json("api", f"repos/{REPO}/issues/{found[0]}")
        parent = subprocess.run(["git", "-C", str(ROOT), "rev-parse", f"{merge}^"], capture_output=True, text=True).stdout.strip()
        checks = list(task_checks(issue.get("body") or ""))
        with tempfile.TemporaryDirectory() as scratch:
            before, after = pathlib.Path(scratch, "parent"), pathlib.Path(scratch, "merge")
            export(parent, before)
            export(merge, after)
            judged = []
            for check in checks:
                test = tuple(check["test"])
                at_parent = verdict(test, *run_check(check["command"], before))
                at_merge = verdict(test, *run_check(check["command"], after))
                if at_parent == "fail" and at_merge == "pass":
                    judged.append(check)
        print(f"task {issue['number']} (pull {number}): {len(checks)} runnable checks, {len(judged)} fail at {parent[:9]} and pass at {merge[:9]}")
        if judged and issue["number"] not in known:
            body = re.sub(r"```teamwork.*?```", "", issue.get("body") or "", flags=re.S).strip()
            tasks.append({"task": issue["number"], "title": issue["title"], "pull": number, "base_sha": parent,
                          "merge_sha": merge, "state": issue["state"], "arms": arms, "body": body, "checks": judged})
            known.add(issue["number"])
    TASKS.write_text(json.dumps(tasks, indent=1) + "\n")
    return 0


def blocked_path(folder):
    """A folder of stand-ins for GitHub, herdr and Claude, first on PATH, so a replay writes to no live board or session."""
    folder.mkdir(parents=True, exist_ok=True)
    for tool in BLOCKED_TOOLS:
        stand_in = folder / tool
        stand_in.write_text(f"#!/bin/sh\necho '{tool} is off in this replay' >&2\nexit 1\n")
        stand_in.chmod(0o755)
    return folder


def weight(model):
    return next((value for key, value in WEIGHT.items() if key in (model or "")), 0.0)


def turn_input(usage):
    creation = usage.get("cache_creation") or {}
    hour = creation.get("ephemeral_1h_input_tokens", 0)
    minutes = creation.get("ephemeral_5m_input_tokens", usage.get("cache_creation_input_tokens", 0) - hour)
    return usage.get("input_tokens", 0) + 1.25 * minutes + 2 * hour + 0.1 * usage.get("cache_read_input_tokens", 0)


def text_of(content):
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content or [] if isinstance(part, dict))


def read_events(stream):
    """The run's init event, hook event names, turns in order, tool uses by id and results in order, and its result event."""
    init, hooks, turns, uses, results, result = {}, [], {}, {}, [], {}
    for position, line in enumerate(stream.splitlines()):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind, subtype = event.get("type"), event.get("subtype", "")
        if kind == "system" and subtype == "init":
            init = event
        elif kind == "system" and subtype == "hook_response":
            hooks.append(event.get("hook_name") or event.get("hook_event") or "")
        elif kind == "assistant" and event.get("parent_tool_use_id") is None:
            message = event["message"]
            first = turns.get(message.get("id"), {}).get("position", position)
            turns[message.get("id")] = {"id": message.get("id"), "position": first, "usage": message.get("usage") or {},
                                        "model": message.get("model")}
            for part in message.get("content", []):
                if isinstance(part, dict) and part.get("type") == "tool_use":
                    uses[part["id"]] = {"name": part["name"], "input": part.get("input") or {}, "turn": message.get("id")}
        elif kind == "user" and event.get("parent_tool_use_id") is None and isinstance(event["message"].get("content"), list):
            for part in event["message"]["content"]:
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    results.append({"position": position, "id": part.get("tool_use_id"), "text": text_of(part.get("content"))})
        elif kind == "result":
            result = event
    return init, hooks, sorted(turns.values(), key=lambda turn: turn["position"]), uses, results, result


def carry(units_tokens, position, turns):
    """The cost of tokens taken in at POSITION: written by the next turn, read by each turn after it."""
    later = [turn for turn in turns if turn["position"] > position]
    if not later:
        return 0.0
    first = later[0]
    rate = 2.0 if (first["usage"].get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0) else 1.25
    return units_tokens * (weight(first["model"]) * rate + sum(weight(turn["model"]) * 0.1 for turn in later[1:]))


def net_saving(turns, uses, results):
    bash, cuts, refetches = [], [], []
    turn_cost = {id(turn): weight(turn["model"]) * (turn_input(turn["usage"]) + 5 * turn["usage"].get("output_tokens", 0))
                 for turn in turns}
    run_units = sum(turn_cost.values())
    removed_units = 0.0
    for result in results:
        use = uses.get(result["id"]) or {}
        if use.get("name") != "Bash":
            continue
        text = result["text"]
        row = {"id": result["id"], "command": use["input"].get("command", "")[:2000], "chars": len(text),
               "lines": text.count("\n") + 1}
        found, shipped = CUT.search(text), list(SHIPPED_CUT.finditer(text))
        if found or shipped:
            if found:
                cut_lines, total_lines, files = int(found.group(1)), int(found.group(2)), [found.group(3)]
                file_chars = pathlib.Path(files[0]).stat().st_size if pathlib.Path(files[0]).exists() else None
                removed = max((file_chars or 0) - len(text) + len(found.group(0)), 0)
            else:
                cut_lines, total_lines = sum(int(note.group(1)) for note in shipped), sum(int(note.group(2)) for note in shipped)
                files, file_chars = [note.group(5) for note in shipped], sum(int(note.group(4)) for note in shipped)
                removed = max(sum(int(note.group(3)) - len(note.group(0)) for note in shipped), 0)
            units = carry(removed / CHARS_PER_TOKEN, result["position"], turns)
            removed_units += units
            row["cut"] = {"lines_cut": cut_lines, "lines": total_lines, "file": files[0], "files": files,
                          "file_chars": file_chars, "removed_chars": removed, "removed_units": round(units, 1)}
            for file in files:
                cuts.append({"file": file, "position": result["position"],
                             "sources": set(SOURCE_FILE.findall(use["input"].get("command", "")))})
        bash.append(row)
    refetch_units = 0.0
    for result in results:
        use = uses.get(result["id"]) or {}
        named = json.dumps(use.get("input"))
        for cut in cuts:
            if cut["position"] < result["position"] and cut["file"] in named:
                issuing = next((turn for turn in turns if turn["id"] == use.get("turn")), None)
                units = carry(len(result["text"]) / CHARS_PER_TOKEN, result["position"], turns)
                turn_units = turn_cost[id(issuing)] if issuing else 0.0
                refetch_units += units + turn_units
                refetches.append({"id": result["id"], "file": cut["file"], "chars": len(result["text"]),
                                  "units": round(units + turn_units, 1)})
                break
    reread_units, reread_carry, rereads = 0.0, 0.0, []
    reads = [result for result in results if (uses.get(result["id"]) or {}).get("name") in ("Bash", "Read")]
    for cut in cuts:
        after = [result for result in reads if result["position"] > cut["position"]][:REREAD_WINDOW]
        for result in after:
            use = uses[result["id"]]
            named = set(SOURCE_FILE.findall(json.dumps(use["input"])))
            if cut["sources"] & named and result["id"] not in {row["id"] for row in rereads}:
                issuing = next((turn for turn in turns if turn["id"] == use.get("turn")), None)
                units = carry(len(result["text"]) / CHARS_PER_TOKEN, result["position"], turns)
                turn_units = turn_cost[id(issuing)] if issuing else 0.0
                reread_units += units + turn_units
                reread_carry += units
                rereads.append({"id": result["id"], "files": sorted(cut["sources"] & named), "chars": len(result["text"]),
                                "units": round(units + turn_units, 1)})
    net = removed_units - refetch_units
    charged = net - reread_units
    share = lambda value: round(value / (run_units + value), 4) if run_units + value else 0.0
    return bash, refetches + [{**row, "reread": True} for row in rereads], {
        "removed_units": round(removed_units, 1), "refetch_units": round(refetch_units, 1), "reread_units": round(reread_units, 1),
        "net_units": round(net, 1), "run_units": round(run_units, 1), "net_share": share(net),
        "net_share_reread_results_charged": share(net - reread_carry), "net_share_rereads_charged": share(charged)}


def hook_identity(arm):
    if arm != "teamwork-cap":
        return None
    return {"path": str(SHIPPED_HOOK.relative_to(ROOT)), "sha256": hashlib.sha256(SHIPPED_HOOK.read_bytes()).hexdigest()}


def record_path(task, arm, repeat):
    return RECORDS / f"{task}-{arm}-{repeat}.json"


def run_one(task, arm, repeat):
    tasks = {entry["task"]: entry for entry in json.loads(TASKS.read_text())}
    entry = tasks[int(task)]
    started = time.time()
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started))
    scratch = pathlib.Path(tempfile.mkdtemp(prefix=f"replay-{task}-{arm}-{repeat}-"))
    work = scratch / "repository"
    export(entry["base_sha"], work)
    stand_ins = blocked_path(scratch / "blocked")
    empty_gh = scratch / "gh-config"
    empty_gh.mkdir()
    environment = {**os.environ, **SWITCHES, "PATH": f"{stand_ins}:{os.environ['PATH']}", "GH_TOKEN": "off-in-replay",
                   "GH_CONFIG_DIR": str(empty_gh)}
    for key in [key for key in environment if key.startswith("HERDR")]:
        environment.pop(key)
    # resolved before the stand-ins go first on PATH, which would otherwise answer for claude itself
    command = [shutil.which("claude"), "-p", PROMPT.format(number=entry["task"], title=entry["title"], body=entry["body"]), "--model", MODEL,
               "--setting-sources", "", "--strict-mcp-config", "--max-budget-usd", BUDGET, "--permission-mode", "acceptEdits",
               "--allowedTools", "Bash", "Read", "Edit", "Write", "Grep", "Glob", "--output-format", "stream-json", "--verbose",
               "--include-hook-events", "--no-session-persistence"]
    if ARMS[arm]:
        command += ["--plugin-dir", str(ARMS[arm])]
    try:
        done = subprocess.run(command, cwd=work, env=environment, capture_output=True, text=True, timeout=RUN_TIMEOUT,
                              stdin=subprocess.DEVNULL)
        stream, errors = done.stdout, done.stderr
    except subprocess.TimeoutExpired as expired:
        stream = expired.stdout.decode() if isinstance(expired.stdout, bytes) else expired.stdout or ""
        errors = f"timed out after {RUN_TIMEOUT} s"
    STREAMS.mkdir(exist_ok=True)
    (STREAMS / f"{task}-{arm}-{repeat}.jsonl").write_text(stream)
    init, hooks, turns, uses, results, result = read_events(stream)
    bash, refetches, saving = net_saving(turns, uses, results)
    checks = []
    for check in entry["checks"]:
        status, out = run_check(check["command"], work)
        checks.append({"index": check["index"], "command": check["command"], "test": check["test"],
                       "result": verdict(tuple(check["test"]), status, out), "output": out[:400]})
    record = {
        "task": entry["task"], "pull": entry["pull"], "base_sha": entry["base_sha"], "arm": arm, "repeat": int(repeat),
        "command": ["claude"] + [part if index != 2 else "<prompt>" for index, part in enumerate(command) if index],
        "prompt": command[2], "environment": SWITCHES, "blocked_tools": list(BLOCKED_TOOLS),
        "init": {"plugins": [plugin.get("name") for plugin in init.get("plugins", [])], "mcp_servers": init.get("mcp_servers", []),
                 "model": init.get("model")},
        "hook_events": hooks, "total_cost_usd": result.get("total_cost_usd"), "models": sorted((result.get("modelUsage") or {}).keys()),
        "is_error": result.get("is_error"), "subtype": result.get("subtype"), "num_turns": result.get("num_turns"),
        "turns": [{"model": turn["model"], "usage": {key: turn["usage"].get(key) for key in
                   ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens", "cache_creation")}}
                  for turn in turns],
        "bash_results": bash, "refetches": refetches, "saving": saving, "checks": checks,
        "started": started_at, "hook": hook_identity(arm), "stderr": errors[-2000:], "passed": all(check["result"] == "pass" for check in checks), "seconds": round(time.time() - started),
    }
    RECORDS.mkdir(exist_ok=True)
    record_path(task, arm, repeat).write_text(json.dumps(record, indent=1) + "\n")
    shutil.rmtree(scratch, ignore_errors=True)
    print(f"{task} {arm} {repeat}: {'pass' if record['passed'] else 'fail'}, ${record['total_cost_usd']}, "
          f"net saving {saving['net_share']:.2%}, {record['seconds']} s")
    return 0


def reparse():
    """Recompute each record's saving from its kept stream, so a change to the arithmetic needs no paid rerun."""
    for path in sorted(RECORDS.glob("*.json")):
        stream = STREAMS / f"{path.stem}.jsonl"
        if not stream.exists():
            print(f"{path.stem}: no stream kept")
            continue
        record = json.loads(path.read_text())
        _, _, turns, uses, results, _ = read_events(stream.read_text())
        record["bash_results"], record["refetches"], record["saving"] = net_saving(turns, uses, results)
        path.write_text(json.dumps(record, indent=1) + "\n")
    return 0


def records():
    return [json.loads(path.read_text()) for path in sorted(RECORDS.glob("*.json"))] if RECORDS.exists() else []


def spent(tasks=None):
    return sum(record.get("total_cost_usd") or 0.0 for record in records() if tasks is None or record["task"] in tasks)


def run_all(repeats, limit, parallel, arms, chosen):
    entries = [entry for entry in task_list() if not chosen or entry["task"] in chosen]
    # the limit counts only the chosen tasks' records, so #1159's spend does not eat a later replay's
    scope = {entry["task"] for entry in entries} if chosen else None
    spent_here = lambda: spent(scope)
    todo = [(entry["task"], arm, repeat) for repeat in range(1, repeats + 1) for entry in entries for arm in task_arms(entry)
            if (not arms or arm in arms) and not record_path(entry["task"], arm, repeat).exists()]
    with concurrent.futures.ThreadPoolExecutor(parallel) as pool:
        running = []
        for job in todo:
            # each run may spend up to its budget, so the next one starts only while the worst case stays under the limit
            while len(running) >= parallel:
                done, pending = concurrent.futures.wait(running, return_when=concurrent.futures.FIRST_COMPLETED)
                running = list(pending)
            if spent_here() + float(BUDGET) * (len(running) + 1) > limit:
                print(f"stop: ${spent_here():.2f} spent; another run could pass ${limit:.0f}")
                break
            running.append(pool.submit(run_one, *job))
        concurrent.futures.wait(running)
    print(f"spent ${spent_here():.2f} over the chosen tasks' records")
    return 0


def count(what):
    rows = records()
    if what == "tasks":
        return len({row["task"] for row in rows})
    if what == "fewest-runs":
        tasks = {row["task"] for row in rows}
        cells = [sum(1 for row in rows if row["task"] == task and row["arm"] == arm) for task in tasks for arm in arms_of(task)]
        return min(cells) if cells else 0
    return None


def clean(row):
    command = row["command"]
    flags_ok = all(any(command[i:i + len(flag)] == flag for i in range(len(command))) for flag in CLEAN_FLAGS)
    plugins = [name for name in row["init"]["plugins"] if not BUILT_IN.match(name)]
    arm = ARMS[row["arm"]]
    plugins_ok = plugins == ([json.loads((arm / ".claude-plugin/plugin.json").read_text())["name"]] if arm else [])
    allowed = ARM_HOOKS[row["arm"]]
    hooks_ok = all(allowed and name.startswith(allowed) for name in row["hook_events"])
    return flags_ok and row["environment"] == SWITCHES and not row["init"]["mcp_servers"] and plugins_ok and hooks_ok


def complete(row):
    needed = ("task", "base_sha", "arm", "command", "environment", "total_cost_usd", "turns", "bash_results", "refetches",
              "saving", "checks")
    return all(row.get(key) is not None for key in needed) and row["checks"] and all(
        check["result"] in ("pass", "fail") for check in row["checks"])


def probe_arms():
    hook = ARMS["output-cap"] / "hooks" / "cap-bash-output.py"
    cases = {"seq 51": (51, True), "seq 50": (50, False), "echo hi; false": (None, False),
             "cd /tmp && seq 60": (60, True), "cat <<'EOF'\nheredoc line\nEOF": (None, False)}
    for command, (lines, cut) in cases.items():
        event = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
        rewritten = json.loads(subprocess.run([str(hook)], input=event, capture_output=True, text=True).stdout)
        wrapped = rewritten["hookSpecificOutput"]["updatedInput"]["command"]
        done = subprocess.run(["bash", "-c", wrapped], capture_output=True, text=True)
        shown = done.stdout.splitlines()
        found = CUT.search(done.stdout)
        if cut and not (found and len(shown) == 51 and shown[:40] == [str(n) for n in range(1, 41)]
                        and shown[-10:] == [str(n) for n in range(lines - 9, lines + 1)]
                        and len(pathlib.Path(found.group(3)).read_text().splitlines()) == lines):
            return f"fail: {command!r} not cut to 40 and 10 lines with a file of all {lines}"
        if not cut and found:
            return f"fail: {command!r} cut"
        if command == "seq 50" and len(shown) != 50:
            return "fail: 50 lines not shown whole"
        if command == "echo hi; false" and done.returncode != 1:
            return f"fail: status {done.returncode}, not 1"
        if command.startswith("cat") and shown != ["heredoc line"]:
            return f"fail: heredoc shown as {shown!r}"
    background = json.dumps({"tool_name": "Bash", "tool_input": {"command": "seq 99", "run_in_background": True}})
    if subprocess.run([str(hook)], input=background, capture_output=True, text=True).stdout.strip():
        return "fail: a background call rewritten"
    return "ok"


def tool_response(command, cwd=None):
    done = subprocess.run(["bash", "-c", command], capture_output=True, text=True, cwd=cwd)
    return done.returncode, {"stdout": done.stdout, "stderr": done.stderr, "interrupted": False, "isImage": False,
                             "returnCodeInterpretation": f"exit {done.returncode}"}


def shipped_hook(command, response):
    event = json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": command},
                        "tool_response": response})
    out = subprocess.run([str(SHIPPED_HOOK)], input=event, capture_output=True, text=True).stdout.strip()
    return json.loads(out)["hookSpecificOutput"]["updatedToolOutput"] if out else None


def split_note(text):
    """The text before a shipped note, the note and the text after it, or None when no note."""
    found = SHIPPED_CUT.search(text)
    return (text[:found.start()], found, text[found.end():]) if found else None


def probe_arm(arm):
    if arm != "teamwork-cap" or not SHIPPED_HOOK.exists():
        return "missing"
    numbers = lambda first, last: "\n".join(str(n) for n in range(first, last + 1))
    with tempfile.TemporaryDirectory() as scratch:
        status, response = tool_response("seq 51")
        updated = shipped_hook("seq 51", response)
        parts = updated and split_note(updated["stdout"])
        if not parts or parts[0] != numbers(1, 40) + "\n" or parts[2] != "\n" + numbers(42, 51) + "\n" \
                or pathlib.Path(parts[1].group(5)).read_text() != response["stdout"]:
            return "fail: 51 lines not cut to the first 40, a note and the last 10 with a file of all 51"
        if shipped_hook("seq 50", tool_response("seq 50")[1]) is not None:
            return "fail: 50 lines rewritten"
        pathlib.Path(scratch, "long.txt").write_text(numbers(1, 200) + "\n")
        for command in ("cat long.txt", "sed -n 1,200p long.txt", "head -200 long.txt", "tail -200 long.txt"):
            if shipped_hook(command, tool_response(command, scratch)[1]) is not None:
                return f"fail: the file read {command!r} rewritten"
        line = "python3 -c 'print(\"x\" * 20000)'"
        updated = shipped_hook(line, tool_response(line)[1])
        parts = updated and split_note(updated["stdout"])
        if not parts or len(parts[0].rstrip("\n")) + len(parts[2].strip("\n")) > 8000:
            return "fail: a 20,000-character line not cut to at most 8,000 characters and the note"
        for command, last in (("trap 'echo trapped' EXIT; seq 60", "trapped"), ("exec seq 60", "60")):
            updated = shipped_hook(command, tool_response(command)[1])
            if not updated or updated["stdout"].splitlines()[-1] != last:
                return f"fail: {command!r} does not end with {last!r} after the cut"
        status, response = tool_response("seq 60; false")
        updated = shipped_hook("seq 60; false", response)
        if status != 1 or not updated or any(updated[key] != response[key] for key in response if key != "stdout"):
            return "fail: a failing call's status or other fields changed"
        status, response = tool_response("seq 60 >&2; echo out")
        updated = shipped_hook("seq 60 >&2; echo out", response)
        if not updated or updated["stdout"] != "out\n" or not split_note(updated["stderr"]):
            return "fail: stderr not capped apart from stdout"
    return "ok"


def probe_allow(arm):
    if arm != "teamwork-cap" or not SHIPPED_HOOK.exists():
        return "missing"
    environment = {**os.environ, **SWITCHES}
    command = [shutil.which("claude"), "-p", "Run the Bash command `seq 80`, then reply with the single word done.",
               "--model", "haiku", "--setting-sources", "", "--strict-mcp-config", "--max-budget-usd", "0.5",
               "--allowedTools", "Bash(seq:*)", "--output-format", "stream-json", "--verbose", "--no-session-persistence",
               "--plugin-dir", str(ARMS[arm])]
    with tempfile.TemporaryDirectory() as scratch:
        stream = subprocess.run(command, cwd=scratch, env=environment, capture_output=True, text=True, timeout=300,
                                stdin=subprocess.DEVNULL).stdout
    _, _, _, _, results, result = read_events(stream)
    if result.get("permission_denials"):
        return f"denied: {result['permission_denials']}"
    return "allowed" if any(SHIPPED_CUT.search(row["text"]) for row in results) else "not cut"


def check_plan(issue):
    comments = gh_json("api", "--paginate", f"repos/{REPO}/issues/{issue}/comments")
    plans = [comment for comment in comments if comment["body"].startswith("REPORTED: replay plan")
             and re.search(r"\b\d+ runs\b", comment["body"]) and re.search(r"\$\d", comment["body"])]
    if not plans:
        return "no plan"
    starts = [row["started"] for row in new_rows() if row.get("started")]
    return "before" if not starts or plans[0]["created_at"] < min(starts) else "after"


def new_tasks():
    return [entry for entry in task_list() if task_arms(entry) == NEW_ARMS]


def new_rows():
    numbers = {entry["task"] for entry in new_tasks()}
    return [row for row in records() if row["task"] in numbers]


def first_word(command):
    # a leading `cd <dir> &&` or `;` only sets the folder, so the program is the word after it
    command = re.sub(r"^(?:\s*cd\s+\S+\s*(?:&&|;)\s*)+", "", command)
    return (command.split() or [""])[0]


def check_measured(arm):
    tasks, rows = new_tasks(), new_rows()
    if arm != "teamwork-cap" or not rows:
        return "missing"
    runs = lambda task, which: [row for row in rows if row["task"] == task and row["arm"] == which]
    covered = [entry["task"] for entry in tasks if entry.get("state") == "closed"
               and len(runs(entry["task"], "none")) >= 2 and len(runs(entry["task"], arm)) >= 2]
    if len(covered) < 6:
        return f"only {len(covered)} closed tasks with 2 runs of each arm"
    program_cuts = {task: [result["command"] for row in runs(task, arm) for result in row["bash_results"]
                           if "cut" in result and not FILE_READ.search(result["command"])] for task in covered}
    cut_tasks = [task for task, commands in program_cuts.items() if commands]
    words = {first_word(command) for commands in program_cuts.values() for command in commands}
    if len(cut_tasks) < 4 or len(words) < 3:
        return f"program-output cuts in {len(cut_tasks)} tasks with first words {sorted(words)}"
    if not all(complete(row) and clean(row) for row in rows):
        return "a record incomplete or unclean"
    models = [model for row in rows for model in row["models"] + [turn["model"] for turn in row["turns"]]]
    if not all(model.startswith("claude-sonnet-") for model in models):
        return f"models {sorted(set(models))}"
    identity = hook_identity(arm)
    if any(row["hook"] != identity for row in rows if row["arm"] == arm):
        return "a record ran another hook than the current file"
    cost = sum(row["total_cost_usd"] or 0 for row in rows)
    return "measured" if cost <= NEW_LIMIT else f"cost ${cost:.2f}"


def gain(arm):
    rows = new_rows()
    capped = [row for row in rows if row["arm"] == arm]
    passed = lambda which: sum(row["passed"] for row in rows if row["arm"] == which)
    mean = sum(row["saving"]["net_share_reread_results_charged"] for row in capped) / len(capped)
    return passed(arm) >= passed("none") and mean > 0, passed("none"), passed(arm), mean


def check_landing():
    if check_measured("teamwork-cap") != "measured":
        return "unmeasured"
    held, *_ = gain("teamwork-cap")
    wired = "cap-program-output" in (ROOT / "teamwork" / "hooks" / "hooks.json").read_text()
    return "ok" if held == wired else ("wired without a gain" if wired else "gain not wired")


def summary():
    rows = records()
    spread = lambda values: f"{min(values):.2%} / {sum(values) / len(values):.2%} / {max(values):.2%}"
    print("| arm | runs | passed | mean cost $ | estimated net saving (min / mean / max) | re-read results charged | "
          "re-read results and turns charged |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for arm in ARMS:
        mine = [row for row in rows if row["arm"] == arm]
        if not mine:
            continue
        estimate = [spread([row["saving"][key] for row in mine]) if arm != "none" else ""
                    for key in ("net_share", "net_share_reread_results_charged", "net_share_rereads_charged")]
        cost = sum(row["total_cost_usd"] or 0 for row in mine) / len(mine)
        print(f"| {arm} | {len(mine)} | {sum(row['passed'] for row in mine)} | {cost:.3f} | {estimate[0]} | {estimate[1]} | {estimate[2]} |")
    print()
    print("| task | passed none / cap | mean cost none $ | mean cost cap $ | observed cost change | cuts | re-reads | "
          "estimated / re-read results / re-read turns charged |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- |")
    changes = []
    for task in sorted({row["task"] for row in rows}):
        capped_arm = arms_of(task)[1]
        arms = {arm: [row for row in rows if row["task"] == task and row["arm"] == arm] for arm in arms_of(task)}
        if not all(arms.values()):
            continue
        cost = {arm: sum(row["total_cost_usd"] or 0 for row in mine) / len(mine) for arm, mine in arms.items()}
        change = cost[capped_arm] / cost["none"] - 1
        changes.append(change)
        capped = arms[capped_arm]
        cuts = sum(1 for row in capped for result in row["bash_results"] if "cut" in result)
        rereads = sum(1 for row in capped for fetch in row["refetches"] if fetch.get("reread"))
        mean = lambda key: sum(row["saving"][key] for row in capped) / len(capped)
        print(f"| {task} | {sum(row['passed'] for row in arms['none'])} / {sum(row['passed'] for row in capped)} | "
              f"{cost['none']:.3f} | {cost[capped_arm]:.3f} | {change:+.1%} | {cuts} | {rereads} | "
              f"{mean('net_share'):.1%} / {mean('net_share_reread_results_charged'):.1%} / {mean('net_share_rereads_charged'):.1%} |")
    capped_bash = [result for row in rows if row["arm"] == "output-cap" for result in row["bash_results"]]
    cut = [result for result in capped_bash if "cut" in result]
    print(f"\ncuts whose command reads a file with cat, sed, head or tail: {sum(bool(FILE_READ.search(result['command'])) for result in cut)} of {len(cut)}")
    shipped = [result for row in rows if row["arm"] == "teamwork-cap" for result in row["bash_results"] if "cut" in result]
    if shipped:
        print(f"teamwork-cap cuts by first word: {sorted({first_word(result['command']) for result in shipped})}, {len(shipped)} cuts")
        held, none_passed, capped_passed, mean = gain("teamwork-cap")
        print(f"teamwork-cap gain on the new tasks: passed {capped_passed} against none's {none_passed}, mean net saving with "
              f"re-read results charged {mean:.2%}; {'holds, so wire the hook' if held else 'does not hold, so leave the hook unwired'}")
    print(f"cap-arm Bash calls that set a trap or exec, which the cap cannot wrap: "
          f"{sum(bool(CAP_BREAKER.search(result['command'])) for result in capped_bash)} of {len(capped_bash)}")
    print(f"later reads of a saved file: {sum(1 for row in rows for fetch in row['refetches'] if not fetch.get('reread'))}")
    if changes:
        print(f"\nobserved cost change, cap over none, mean of tasks: {sum(changes) / len(changes):+.1%} (min {min(changes):+.1%}, max {max(changes):+.1%})")
    print(f"spent ${spent():.2f}, of which ${spent({entry['task'] for entry in new_tasks()}):.2f} on the teamwork-cap tasks. Reading: the cap is worth building only when its arm passes as often as none, its net saving "
          "with re-reads charged stays above 0, and the observed cost change does not contradict it.")
    return 0


def main(args):
    usage = lambda: (print(__doc__, file=sys.stderr), 2)[1]
    if not args:
        return usage()
    verb, rest = args[0], args[1:]
    rows = records
    if verb == "--list-arms" and not rest:
        print(",".join(ARMS))
    elif verb == "--pick-tasks" and rest:
        arms = FIRST_ARMS
        if rest[0] == "--arms" and len(rest) > 2:
            arms, rest = rest[1].split(","), rest[2:]
        if not set(arms) <= set(ARMS):
            return usage()
        return pick_tasks(rest, arms)
    elif verb == "--run" and len(rest) == 3 and rest[1] in ARMS:
        return run_one(*rest)
    elif verb == "--run-all":
        options = {"--repeats": "2", "--max-dollars": str(LIMIT), "--parallel": "3", "--arms": "", "--tasks": ""}
        while rest:
            if rest[0] not in options or len(rest) < 2:
                return usage()
            options[rest[0]], rest = rest[1], rest[2:]
        arms = [arm for arm in options["--arms"].split(",") if arm]
        chosen = {int(task) for task in options["--tasks"].split(",") if task}
        if not set(arms) <= set(ARMS):
            return usage()
        return run_all(int(options["--repeats"]), float(options["--max-dollars"]), int(options["--parallel"]), arms, chosen)
    elif verb == "--count" and len(rest) == 1 and rest[0] in ("tasks", "fewest-runs"):
        print(count(rest[0]))
    elif verb == "--check-records" and not rest:
        print("complete" if rows() and all(complete(row) for row in rows()) else "incomplete")
    elif verb == "--check-clean" and not rest:
        print("clean" if rows() and all(clean(row) for row in rows()) else "unclean")
    elif verb == "--check-firing" and not rest:
        cut = lambda row: any("cut" in result for result in row["bash_results"])
        fired = any(cut(row) for row in rows() if row["arm"] == "output-cap") and not any(cut(row) for row in rows() if row["arm"] == "none")
        print("fired" if fired else "not fired")
    elif verb == "--check-spend" and not rest:
        print("within-120" if rows() and spent() <= LIMIT else f"spent {spent():.2f}")
    elif verb == "--check-models" and not rest:
        print("claude-only" if rows() and all(model.startswith("claude-") for row in rows() for model in row["models"] + [
            turn["model"] for turn in row["turns"]]) else "other model")
    elif verb == "--probe-arms" and not rest:
        print(probe_arms())
    elif verb == "--probe-arm" and len(rest) == 1:
        print(probe_arm(rest[0]))
    elif verb == "--probe-allow" and len(rest) == 1:
        print(probe_allow(rest[0]))
    elif verb == "--check-plan" and len(rest) == 1 and rest[0].isdigit():
        print(check_plan(int(rest[0])))
    elif verb == "--check-measured" and len(rest) == 1:
        print(check_measured(rest[0]))
    elif verb == "--check-landing" and not rest:
        print(check_landing())
    elif verb == "--reparse" and not rest:
        return reparse()
    elif verb == "--summary" and not rest:
        return summary()
    else:
        return usage()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

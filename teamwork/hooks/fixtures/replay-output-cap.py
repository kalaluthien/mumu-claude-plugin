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
more than `--max-dollars` (120). `teamwork-cap` runs the arm's PostToolUse hook `cap-program-output.py`; `--probe-arm`
feeds it real Bash output, `--probe-allow` runs it once on Haiku under a `Bash(seq:*)` allow rule only,
`--check-measured` prints `no gain` or `gain` from the new tasks' records, and `--check-landing` prints `unshipped`
while the teamwork plugin carries no such hook outside its fixtures.
A run's net saving is the cut tokens' carry to the run's end, less each later call that read a cut output's file: its
result's carry and its turn's cost; tokens are characters over 2.2, priced as measure-context-share.py prices them."""
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
import replay_runs  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
RECORDS = HERE / "output-cap-runs"
# raw streams stay outside the repository, being megabytes each, so a record can be re-read without a paid rerun
STREAMS = pathlib.Path(tempfile.gettempdir(), "replay-output-cap-streams")
TASKS = HERE / "output-cap-tasks.json"
ARMS = {"none": None, "output-cap": HERE / "output-cap-arm", "teamwork-cap": HERE / "teamwork-cap-arm"}
# the arm whose hook each arm runs, as the init event names its hook events
ARM_HOOKS = {"none": None, "output-cap": "PreToolUse:Bash", "teamwork-cap": "PostToolUse:Bash"}
CAP_HOOK = HERE / "teamwork-cap-arm" / "hooks" / "cap-program-output.py"
# #1159's tasks replay the test arm; any task picked later replays the PostToolUse cap
FIRST_ARMS = ["none", "output-cap"]
NEW_ARMS = ["none", "teamwork-cap"]
NEW_LIMIT = 20.0
MIN_GAIN = 0.01
PLAN_ISSUE = 1172
REPO = "kalaluthien/mumu-claude-plugin"
MODEL, BUDGET, LIMIT = "sonnet", "5", 120.0
CLEAN_FLAGS = [["--setting-sources", ""], ["--strict-mcp-config"], ["--max-budget-usd", BUDGET]]
CUT = re.compile(r"\[output cap: (\d+) of (\d+) lines cut here; all of them are in (\S+);")
# the PostToolUse cap's note also counts characters and may appear once per stream
PROGRAM_CUT = re.compile(r"\[output cap: (\d+) of (\d+) lines and (\d+) of (\d+) characters cut here; all of them are in (\S+); "
                         r"read a range of that file, not all of it\]")
# a check that reaches outside the export would judge the live machine, not the run
OUTSIDE = re.compile(r"\b(?:gh|herdr|claude|curl)\b|https?://|/Users/|~/|\$HOME|origin/")
# a later call naming a file the cut command read may be the model fetching the cut part again by another range
SOURCE_FILE = re.compile(r"[\w.-]+\.(?:py|md|json|jsonl|sh|txt|ya?ml|toml)\b")
REREAD_WINDOW = 2
FILE_READ = re.compile(r"\b(?:cat|sed|head|tail)\b")
SHELL_ONLY = {"cd", "echo", "printf", "true", "false", "set", "export", "EOF"}
# a command that sets its own EXIT trap or execs replaces the cap's trap, so its output would vanish
CAP_BREAKER = re.compile(r"\btrap\b|(?:^|[;&|]\s*)exec\b")
PROMPT = """You are replaying a past task in a fresh checkout of the mumu-claude-plugin repository, your working folder.
Do the task below fully: change the files so that each `[check]` of its Definition of done passes, run the checks you can,
then commit your change with git. GitHub, herdr and other Claude sessions are off in this replay: skip each step that reads
or writes an issue, pull request, comment or session (filing, commenting, judging, pushing, telling), and each check
that needs one.

Task #{number}: {title}

{body}"""


def gh_json(*args):
    return json.loads(subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout)


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
    tasks = task_list()
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
            replay_runs.export(ROOT, parent, before)
            replay_runs.export(ROOT, merge, after)
            judged = []
            for check in checks:
                test = tuple(check["test"])
                at_parent = replay_runs.verdict(test, *replay_runs.run_check(check["command"], before))
                at_merge = replay_runs.verdict(test, *replay_runs.run_check(check["command"], after))
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


def net_saving(turns, uses, results):
    bash, cuts, refetches = [], [], []
    turn_cost = {id(turn): replay_runs.turn_units(turn) for turn in turns}
    run_units = replay_runs.run_units(turns)
    removed_units = 0.0
    for result in results:
        use = uses.get(result["id"]) or {}
        if use.get("name") != "Bash":
            continue
        text = result["text"]
        row = {"id": result["id"], "command": use["input"].get("command", "")[:2000], "chars": len(text),
               "lines": text.count("\n") + 1}
        found, notes = CUT.search(text), list(PROGRAM_CUT.finditer(text))
        if found or notes:
            if found:
                cut_lines, total_lines, files = int(found.group(1)), int(found.group(2)), [found.group(3)]
                file_chars = pathlib.Path(files[0]).stat().st_size if pathlib.Path(files[0]).exists() else None
                removed = max((file_chars or 0) - len(text) + len(found.group(0)), 0)
            else:
                cut_lines, total_lines = sum(int(note.group(1)) for note in notes), sum(int(note.group(2)) for note in notes)
                files, file_chars = [note.group(5) for note in notes], sum(int(note.group(4)) for note in notes)
                removed = max(sum(int(note.group(3)) - len(note.group(0)) for note in notes), 0)
            units = replay_runs.carry(removed / replay_runs.CHARS_PER_TOKEN, result["position"], turns)
            removed_units += units
            row["cut"] = {"lines_cut": cut_lines, "lines": total_lines, "file": files[0], "files": files,
                          "file_chars": file_chars, "removed_chars": removed, "removed_units": round(units, 1)}
            for file in files:
                cuts.append({"file": file, "position": result["position"],
                             "sources": set(SOURCE_FILE.findall(use["input"].get("command", "")))})
        bash.append(row)

    def later_call(result, use):
        """The carry of a later call's RESULT and the cost of the turn that issued it, summed, and the carry alone."""
        issuing = next((turn for turn in turns if turn["id"] == use.get("turn")), None)
        units = replay_runs.carry(len(result["text"]) / replay_runs.CHARS_PER_TOKEN, result["position"], turns)
        return units + (turn_cost[id(issuing)] if issuing else 0.0), units

    refetch_units = 0.0
    for result in results:
        use = uses.get(result["id"]) or {}
        named = json.dumps(use.get("input"))
        for cut in cuts:
            if cut["position"] < result["position"] and cut["file"] in named:
                charged, _ = later_call(result, use)
                refetch_units += charged
                refetches.append({"id": result["id"], "file": cut["file"], "chars": len(result["text"]), "units": round(charged, 1)})
                break
    reread_units, reread_carry, rereads = 0.0, 0.0, []
    reads = [result for result in results if (uses.get(result["id"]) or {}).get("name") in ("Bash", "Read")]
    for cut in cuts:
        after = [result for result in reads if result["position"] > cut["position"]][:REREAD_WINDOW]
        for result in after:
            use = uses[result["id"]]
            named = set(SOURCE_FILE.findall(json.dumps(use["input"])))
            if cut["sources"] & named and result["id"] not in {row["id"] for row in rereads}:
                charged, units = later_call(result, use)
                reread_units += charged
                reread_carry += units
                rereads.append({"id": result["id"], "files": sorted(cut["sources"] & named), "chars": len(result["text"]),
                                "units": round(charged, 1)})
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
    return {"path": str(CAP_HOOK.relative_to(ROOT)), "sha256": hashlib.sha256(CAP_HOOK.read_bytes()).hexdigest()}


def record_path(task, arm, repeat):
    return RECORDS / f"{task}-{arm}-{repeat}.json"


def run_one(task, arm, repeat):
    entry = next(item for item in task_list() if item["task"] == int(task))
    started = time.time()
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started))
    scratch = pathlib.Path(tempfile.mkdtemp(prefix=f"replay-{task}-{arm}-{repeat}-"))
    work = scratch / "repository"
    replay_runs.export(ROOT, entry["base_sha"], work)
    environment = replay_runs.clean_environment(scratch)
    # resolved before the stand-ins go first on PATH, which would otherwise answer for claude itself
    command = [shutil.which("claude"), "-p", PROMPT.format(number=entry["task"], title=entry["title"], body=entry["body"]), "--model", MODEL,
               "--setting-sources", "", "--strict-mcp-config", "--max-budget-usd", BUDGET, "--permission-mode", "acceptEdits",
               "--allowedTools", "Bash", "Read", "Edit", "Write", "Grep", "Glob", "--output-format", "stream-json", "--verbose",
               "--include-hook-events", "--no-session-persistence"]
    if ARMS[arm]:
        command += ["--plugin-dir", str(ARMS[arm])]
    stream, errors = replay_runs.run_claude(command, work, environment)
    STREAMS.mkdir(exist_ok=True)
    (STREAMS / f"{task}-{arm}-{repeat}.jsonl").write_text(stream)
    init, hooks, turns, uses, results, result = replay_runs.read_events(stream)
    bash, refetches, saving = net_saving(turns, uses, results)
    checks = []
    for check in entry["checks"]:
        status, out = replay_runs.run_check(check["command"], work)
        checks.append({"index": check["index"], "command": check["command"], "test": check["test"],
                       "result": replay_runs.verdict(tuple(check["test"]), status, out), "output": out[:400]})
    record = {
        "task": entry["task"], "pull": entry["pull"], "base_sha": entry["base_sha"], "arm": arm, "repeat": int(repeat),
        "command": ["claude"] + [part if index != 2 else "<prompt>" for index, part in enumerate(command) if index],
        "prompt": command[2], "environment": replay_runs.SWITCHES, "blocked_tools": list(replay_runs.BLOCKED_TOOLS),
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
        _, _, turns, uses, results, _ = replay_runs.read_events(stream.read_text())
        record["bash_results"], record["refetches"], record["saving"] = net_saving(turns, uses, results)
        path.write_text(json.dumps(record, indent=1) + "\n")
    return 0


def records():
    return replay_runs.read_records(RECORDS)


def spent(tasks=None):
    return sum(record.get("total_cost_usd") or 0.0 for record in records() if tasks is None or record["task"] in tasks)


def run_all(repeats, limit, parallel, arms, chosen):
    entries = [entry for entry in task_list() if not chosen or entry["task"] in chosen]
    # the limit counts only the chosen tasks' records, so #1159's spend does not eat a later replay's
    scope = {entry["task"] for entry in entries} if chosen else None
    spent_here = lambda: spent(scope)
    todo = [(entry["task"], arm, repeat) for repeat in range(1, repeats + 1) for entry in entries for arm in task_arms(entry)
            if (not arms or arm in arms) and not record_path(entry["task"], arm, repeat).exists()]
    replay_runs.run_jobs(todo, run_one, parallel, spent_here, BUDGET, limit)
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
    plugins = [name for name in row["init"]["plugins"] if not name.startswith(replay_runs.BUILT_IN_PLUGIN_PREFIX)]
    arm = ARMS[row["arm"]]
    plugins_ok = plugins == ([json.loads((arm / ".claude-plugin/plugin.json").read_text())["name"]] if arm else [])
    allowed = ARM_HOOKS[row["arm"]]
    hooks_ok = all(allowed and name.startswith(allowed) for name in row["hook_events"])
    return flags_ok and row["environment"] == replay_runs.SWITCHES and not row["init"]["mcp_servers"] and plugins_ok and hooks_ok


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


def run_cap_hook(command, response):
    event = json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": command},
                        "tool_response": response})
    out = subprocess.run([str(CAP_HOOK)], input=event, capture_output=True, text=True).stdout.strip()
    return json.loads(out)["hookSpecificOutput"]["updatedToolOutput"] if out else None


def split_note(text):
    """The text before a PostToolUse cap's note, the note and the text after it, or None when no note."""
    found = PROGRAM_CUT.search(text)
    return (text[:found.start()], found, text[found.end():]) if found else None


def probe_arm(arm):
    if arm != "teamwork-cap" or not CAP_HOOK.exists():
        return "missing"
    numbers = lambda first, last: "\n".join(str(n) for n in range(first, last + 1))
    with tempfile.TemporaryDirectory() as scratch:
        status, response = tool_response("seq 51")
        updated = run_cap_hook("seq 51", response)
        parts = updated and split_note(updated["stdout"])
        if not parts or parts[0] != numbers(1, 40) + "\n" or parts[2] != "\n" + numbers(42, 51) + "\n" \
                or pathlib.Path(parts[1].group(5)).read_text() != response["stdout"]:
            return "fail: 51 lines not cut to the first 40, a note and the last 10 with a file of all 51"
        if run_cap_hook("seq 50", tool_response("seq 50")[1]) is not None:
            return "fail: 50 lines rewritten"
        pathlib.Path(scratch, "long.txt").write_text(numbers(1, 200) + "\n")
        for command in ("cat long.txt", "sed -n 1,200p long.txt", "head -200 long.txt", "tail -200 long.txt"):
            if run_cap_hook(command, tool_response(command, scratch)[1]) is not None:
                return f"fail: the file read {command!r} rewritten"
        line = "python3 -c 'print(\"x\" * 20000)'"
        updated = run_cap_hook(line, tool_response(line)[1])
        parts = updated and split_note(updated["stdout"])
        if not parts or len(parts[0].rstrip("\n")) + len(parts[2].strip("\n")) > 8000:
            return "fail: a 20,000-character line not cut to at most 8,000 characters and the note"
        for command, last in (("trap 'echo trapped' EXIT; seq 60", "trapped"), ("exec seq 60", "60")):
            updated = run_cap_hook(command, tool_response(command)[1])
            if not updated or updated["stdout"].splitlines()[-1] != last:
                return f"fail: {command!r} does not end with {last!r} after the cut"
        status, response = tool_response("seq 60; false")
        updated = run_cap_hook("seq 60; false", response)
        if status != 1 or not updated or any(updated[key] != response[key] for key in response if key != "stdout"):
            return "fail: a failing call's status or other fields changed"
        status, response = tool_response("seq 60 >&2; echo out")
        updated = run_cap_hook("seq 60 >&2; echo out", response)
        if not updated or updated["stdout"] != "out\n" or not split_note(updated["stderr"]):
            return "fail: stderr not capped apart from stdout"
    return "ok"


def probe_allow(arm):
    if arm != "teamwork-cap" or not CAP_HOOK.exists():
        return "missing"
    environment = {**os.environ, **replay_runs.SWITCHES}
    command = [shutil.which("claude"), "-p", "Run the Bash command `seq 80`, then reply with the single word done.",
               "--model", "haiku", "--setting-sources", "", "--strict-mcp-config", "--max-budget-usd", "0.5",
               "--allowedTools", "Bash(seq:*)", "--output-format", "stream-json", "--verbose", "--no-session-persistence",
               "--plugin-dir", str(ARMS[arm])]
    with tempfile.TemporaryDirectory() as scratch:
        stream = subprocess.run(command, cwd=scratch, env=environment, capture_output=True, text=True, timeout=300,
                                stdin=subprocess.DEVNULL).stdout
    _, _, _, _, results, result = replay_runs.read_events(stream)
    if result.get("permission_denials"):
        return f"denied: {result['permission_denials']}"
    return "allowed" if any(PROGRAM_CUT.search(row["text"]) for row in results) else "not cut"


def check_plan(issue):
    comments = gh_json("api", "--paginate", f"repos/{REPO}/issues/{issue}/comments")
    plans = [comment for comment in comments if comment["body"].startswith("REPORTED: replay plan")
             and re.search(r"\b\d+ runs\b", comment["body"]) and re.search(r"\$\d", comment["body"])]
    if not plans:
        return "no plan"
    starts = [row["started"] for row in new_records() if row.get("started")]
    return "before" if not starts or plans[0]["created_at"] < min(starts) else "after"


def new_tasks():
    return [entry for entry in task_list() if task_arms(entry) == NEW_ARMS]


def new_records():
    numbers = {entry["task"] for entry in new_tasks()}
    return [row for row in records() if row["task"] in numbers]


def segment_words(command):
    """The program word of each `;`, `&&`, `||`, `|` or line-separated part of a command, a leading `VAR=…` skipped."""
    parts = re.split(r"\|\||&&|[;|\n]", command)
    words = [re.sub(r"^(?:\s*\w+=\S*(?:\s+|$))*", "", part).split()[:1] for part in parts]
    return [word[0] for word in words if word]


def mixed_read(command):
    """A call the PostToolUse cap left whole as a file read although it also ran another program, such as `ls` or `grep`."""
    return bool(FILE_READ.search(command)) and any(word not in SHELL_ONLY and not FILE_READ.fullmatch(word)
                                                   for word in segment_words(command))


def first_word(command):
    # a `cd`, `echo` or `VAR=…` part only sets the stage, so the program is the first other word
    return next((word for word in segment_words(command) if word not in SHELL_ONLY), "")


def check_measured(arm):
    """`gain` or `no gain` from the new tasks' records, once they are whole, clean, on Sonnet and from the current hook."""
    tasks, rows = new_tasks(), new_records()
    if arm != "teamwork-cap" or not rows:
        return "missing"
    capped = [row for row in rows if row["arm"] == arm]
    covered = {entry["task"] for entry in tasks if entry.get("state") == "closed"} & {row["task"] for row in capped}
    if len(covered) < 6:
        return f"only {len(covered)} closed tasks with a {arm} run"
    if not all(complete(row) and clean(row) for row in rows):
        return "a record incomplete or unclean"
    models = [model for row in rows for model in row["models"] + [turn["model"] for turn in row["turns"]]]
    if not all(model.startswith("claude-sonnet-") for model in models):
        return f"models {sorted(set(models))}"
    sha = hook_identity(arm)["sha256"]
    if any((row["hook"] or {}).get("sha256") != sha for row in capped):
        return "a record ran another hook than the current file"
    cost = sum(row["total_cost_usd"] or 0 for row in rows)
    if cost > NEW_LIMIT:
        return f"cost ${cost:.2f}"
    cut_tasks = {row["task"] for row in capped for result in row["bash_results"]
                 if "cut" in result and not FILE_READ.search(result["command"])}
    held, *_, mean = gain(arm)
    # a gain needs cuts across most tasks and a saving above run noise, not a hair above 0
    return "gain" if held and len(cut_tasks) >= 4 and mean >= MIN_GAIN else "no gain"


def gain(arm):
    rows = new_records()
    capped = [row for row in rows if row["arm"] == arm]
    passed = lambda which: sum(row["passed"] for row in rows if row["arm"] == which)
    runs = lambda which: sum(1 for row in rows if row["arm"] == which)
    mean = sum(row["saving"]["net_share_reread_results_charged"] for row in capped) / len(capped)
    # pass shares, since the arms may hold different run counts
    return passed(arm) / runs(arm) >= passed("none") / max(runs("none"), 1) and mean > 0, passed("none"), passed(arm), mean


def check_landing():
    """`unshipped` while no teamwork hook outside the fixtures is the cap or wires it."""
    hooks = ROOT / "teamwork" / "hooks"
    named = [path for path in hooks.rglob("*") if path.is_file() and "fixtures" not in path.relative_to(hooks).parts
             and (path.name == CAP_HOOK.name or (path.suffix == ".json" and CAP_HOOK.stem in path.read_text()))]
    return "unshipped" if not named else f"shipped in {', '.join(str(path.relative_to(ROOT)) for path in named)}"


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
    program_cuts = [result for row in rows if row["arm"] == "teamwork-cap" for result in row["bash_results"] if "cut" in result]
    if program_cuts:
        print(f"teamwork-cap cuts by first word: {sorted({first_word(result['command']) for result in program_cuts})}, {len(program_cuts)} cuts")
        capped_rows = [row for row in rows if row["arm"] == "teamwork-cap"]
        long = [result for row in capped_rows for result in row["bash_results"] if result["lines"] > 50 or result["chars"] > 8000]
        whole = [result for result in long if "cut" not in result]
        print(f"teamwork-cap outputs over 50 lines or 8,000 characters: {len(long)}; cut {len(long) - len(whole)}; left whole "
              f"as file reads {sum(bool(FILE_READ.search(result['command'])) for result in whole)}, of which "
              f"{sum(mixed_read(result['command']) for result in whole)} also ran another program (commands kept to 2,000 characters)")
        print(f"teamwork-cap Bash calls left whole as file reads although they ran another program: "
              f"{sum(mixed_read(result['command']) for row in capped_rows for result in row['bash_results'] if 'cut' not in result)} "
              f"of {sum(len(row['bash_results']) for row in capped_rows)}")
        held, none_passed, capped_passed, mean = gain("teamwork-cap")
        print(f"teamwork-cap on the new tasks: passed {capped_passed} against none's {none_passed}, mean net saving with "
              f"re-read results charged {mean:.2%}; --check-measured: {check_measured('teamwork-cap')}")
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
        options = replay_runs.read_options(rest, {"--repeats": "2", "--max-dollars": str(LIMIT), "--parallel": "3", "--arms": "",
                                                  "--tasks": ""})
        if options is None:
            return usage()
        arms = [arm for arm in options["--arms"].split(",") if arm]
        chosen = {int(task) for task in options["--tasks"].split(",") if task}
        if not set(arms) <= set(ARMS):
            return usage()
        return run_all(int(options["--repeats"]), float(options["--max-dollars"]), int(options["--parallel"]), arms, chosen)
    elif verb == "--count" and len(rest) == 1 and rest[0] in ("tasks", "fewest-runs"):
        print(count(rest[0]))
    elif verb == "--check-records" and not rest:
        print("complete" if records() and all(complete(row) for row in records()) else "incomplete")
    elif verb == "--check-clean" and not rest:
        print("clean" if records() and all(clean(row) for row in records()) else "unclean")
    elif verb == "--check-firing" and not rest:
        cut = lambda row: any("cut" in result for result in row["bash_results"])
        fired = any(cut(row) for row in records() if row["arm"] == "output-cap") and not any(cut(row) for row in records() if row["arm"] == "none")
        print("fired" if fired else "not fired")
    elif verb == "--check-spend" and not rest:
        print("within-120" if records() and spent() <= LIMIT else f"spent {spent():.2f}")
    elif verb == "--check-models" and not rest:
        print("claude-only" if records() and all(model.startswith("claude-") for row in records() for model in row["models"] + [
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

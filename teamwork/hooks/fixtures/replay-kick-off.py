#!/usr/bin/env python3
"""Replay closed teamwork tasks as a worker kick-off in clean `claude -p` runs, one arm per version of the kick-off text,
judge each run by its task's own `[check]`s, and keep one record and one stream per run, from which alone every check reads.

usage: replay-kick-off.py --list-arms
usage: replay-kick-off.py --pilot <task> <arm>
usage: replay-kick-off.py --run <task> <arm> <repeat>
usage: replay-kick-off.py --run-all [--repeats <n>] [--max-dollars <x>] [--parallel <n>] [--arms <arm>,...] [--tasks <task>,...]
usage: replay-kick-off.py --count-runs [--repeats <n>] [--arms <arm>,...]
usage: replay-kick-off.py --summary
usage: replay-kick-off.py --check-designs|--check-shipped

An arm is a version of `teamwork/`: `none` is the tree at BASE, `shipped` the tree as it stands, untracked files included. The tasks are four of the six of `output-cap-tasks.json` picked for #1172, each
with checks that fail at its parent and pass at its merge. A run loads its arm as the only plugin, starts the worker kick-off
on the task, and ends at its budget. `--pilot` runs one without keeping a record, to size the plan.
`--summary` prints, per arm, passes, mean run bill, kick-off characters opened and the paired saving against `none`; the bill
counts every turn, so a re-read of text the arm cut is charged already.
Every count reads the kept streams in `kick-off-runs/streams/`, never a record's own figures."""
import concurrent.futures
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import replay_runs  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
RECORDS = HERE / "kick-off-runs"
STREAMS = RECORDS / "streams"
TASKS = HERE / "output-cap-tasks.json"
BASE = "89ee7dbb40354670ad86afe9781cc3202bd2f0c7"
TASK_NUMBERS = (1035, 1168, 1071, 1020)
ISSUE = 1245
LIMIT = 8.0
# the owner's cap counts the three pilot runs ($1.40), the three runs stopped at $0.5 or less each, and the first four `shipped`
# runs ($1.71), whose export lacked the untracked protocol-sessions.md, so no record of them is kept
PRIOR_SPEND = 4.61
REPEATS = 1
MIN_GAIN = 0.01
MODEL, BUDGET = "sonnet", "0.75"
SWITCHES = {"CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}
KICK_OFF = "/plugin/teamwork/skills/kick-off/"
FILE_READ = re.compile(r"^\s*(?:cat|sed|head|tail)\b")
RUN_TIMEOUT = 3600
PROMPT = """Run the teamwork:kick-off skill with these arguments: worker replay-worker manager replay-manager {words}

This is a replay in a fresh checkout of the mumu-claude-plugin repository, your working folder. Follow the skill's route:
Read each file it names before the step it serves. The task below is already defined and its criteria fixed: build it so each `[check]` of its Definition of done passes, run the checks you can, and
commit with git. GitHub, herdr and other Claude sessions are off: skip each step that reads or writes an issue, pull
request, comment or session (filing, commenting, judging, pushing, telling), and each check that needs one.

Task #{number}: {title}

{body}"""


def tasks():
    chosen = {entry["task"]: entry for entry in json.loads(TASKS.read_text())}
    return [chosen[number] for number in TASK_NUMBERS]


def arm_names():
    return ["none", "shipped"]


def tree_hash(folder):
    digest = hashlib.sha256()
    for path in sorted(pathlib.Path(folder).rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(folder)).encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def build_arm(arm, into):
    """The plugin tree of ARM in INTO/teamwork, and the sha-256 of its kick-off folder."""
    into.mkdir(parents=True)
    if arm == "shipped":
        files = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--cached", "--others", "--exclude-standard", "teamwork"], capture_output=True, check=True).stdout
        for name in filter(None, files.decode().split("\0")):
            source = ROOT / name
            if source.is_file():
                (into / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, into / name)
    else:
        archive = subprocess.run(["git", "-C", str(ROOT), "archive", BASE, "teamwork"], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(into)], input=archive, check=True)
    return tree_hash(into / "teamwork" / "skills" / "kick-off")


def head_hash():
    return tree_hash(ROOT / "teamwork" / "skills" / "kick-off")


def record_path(task, arm, repeat):
    return RECORDS / f"{task}-{arm}-{repeat}.json"


def stream_path(task, arm, repeat):
    return STREAMS / f"{task}-{arm}-{repeat}.jsonl"


def run_one(task, arm, repeat, keep=True):
    entry = next(item for item in tasks() if item["task"] == int(task))
    started = time.time()
    scratch = pathlib.Path(tempfile.mkdtemp(prefix=f"kick-off-{task}-{arm}-{repeat}-"))
    work = scratch / "repository"
    replay_runs.export(ROOT, entry["base_sha"], work)
    tree = build_arm(arm, scratch / "plugin")
    empty_gh = scratch / "gh-config"
    empty_gh.mkdir()
    environment = {**os.environ, **SWITCHES, "PATH": f"{replay_runs.blocked_path(scratch / 'blocked')}:{os.environ['PATH']}",
                   "GH_TOKEN": "off-in-replay", "GH_CONFIG_DIR": str(empty_gh)}
    for key in [key for key in environment if key.startswith("HERDR")]:
        environment.pop(key)
    words = f"task {entry['task']}, {entry['title']}"
    command = [shutil.which("claude"), "-p", PROMPT.format(words=words, number=entry["task"], title=entry["title"], body=entry["body"]),
               "--model", MODEL, "--setting-sources", "", "--strict-mcp-config", "--max-budget-usd", BUDGET,
               "--permission-mode", "acceptEdits", "--allowedTools", "Bash", "Read", "Edit", "Write", "Grep", "Glob", "Skill",
               "--plugin-dir", str(scratch / "plugin" / "teamwork"), "--output-format", "stream-json", "--verbose",
               "--no-session-persistence"]
    try:
        done = subprocess.run(command, cwd=work, env=environment, capture_output=True, text=True, timeout=RUN_TIMEOUT,
                              stdin=subprocess.DEVNULL)
        stream, errors = done.stdout, done.stderr
    except subprocess.TimeoutExpired as expired:
        stream = expired.stdout.decode() if isinstance(expired.stdout, bytes) else expired.stdout or ""
        errors = f"timed out after {RUN_TIMEOUT} s"
    checks = []
    for check in entry["checks"]:
        status, out = replay_runs.run_check(check["command"], work)
        checks.append({"index": check["index"], "result": replay_runs.verdict(tuple(check["test"]), status, out), "output": out[:300]})
    shutil.rmtree(scratch, ignore_errors=True)
    passed = all(check["result"] == "pass" for check in checks)
    init, turns, uses, results, result = replay_runs.read_events(stream)
    if not keep:
        kept = pathlib.Path(tempfile.gettempdir(), f"kick-off-pilot-{task}-{arm}.jsonl")
        kept.write_text(stream)
        print(f"stream in {kept}")
        print(f"pilot {task} {arm}: {'pass' if passed else 'fail'}, ${result.get('total_cost_usd')}, {len(turns)} turns, "
              f"{round(time.time() - started)} s, kick-off characters opened {sum(row['chars'] for row in opened(uses, results))}")
        return 0
    STREAMS.mkdir(parents=True, exist_ok=True)
    stream_path(task, arm, repeat).write_text(stream)
    record = {"task": entry["task"], "arm": arm, "repeat": int(repeat), "tree": tree, "base_sha": entry["base_sha"],
              "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "seconds": round(time.time() - started),
              "stream_sha256": hashlib.sha256(stream.encode()).hexdigest(), "cost": result.get("total_cost_usd"),
              "checks": checks, "passed": passed, "stderr": errors[-1000:]}
    record_path(task, arm, repeat).write_text(json.dumps(record, indent=1) + "\n")
    print(f"{task} {arm} {repeat}: {'pass' if passed else 'fail'}, ${record['cost']}, {record['seconds']} s")
    return 0


def opened(uses, results):
    """The kick-off files a run read: a Read of one, or a shell `cat`, `sed`, `head` or `tail` of one, with the result's characters."""
    rows = []
    for result in results:
        use = uses.get(result["id"]) or {}
        named = json.dumps(use.get("input"))
        if KICK_OFF not in named:
            continue
        if use.get("name") == "Read" or (use.get("name") == "Bash" and FILE_READ.match(use["input"].get("command", ""))):
            rows.append({"file": re.search(r"[\w/.-]*" + re.escape(KICK_OFF) + r"[\w/.-]*", named).group(0), "chars": len(result["text"]),
                         "position": result["position"]})
    return rows


def recount(record):
    """What a record's kept stream shows: its hash matches, its clean flags, models, bill and kick-off characters; None when the stream is missing or altered."""
    path = stream_path(record["task"], record["arm"], record["repeat"])
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != record.get("stream_sha256"):
        return None
    init, turns, uses, results, result = replay_runs.read_events(path.read_text())
    plugins = [plugin.get("name") for plugin in init.get("plugins", []) if not str(plugin.get("name", "")).startswith("cc-plugin-")]
    models = {turn["model"] for turn in turns}
    reads = opened(uses, results)
    return {"clean": not init.get("mcp_servers") and plugins == ["teamwork"] and bool(models) and all(
                str(model).startswith("claude-") for model in models) and "-p" not in init.get("slash_commands", []),
            "bill": replay_runs.run_units(turns), "opened": sum(row["chars"] for row in reads),
            "unit_per_char": (sum(replay_runs.carry(row["chars"] / replay_runs.CHARS_PER_TOKEN, row["position"], turns) for row in reads)
                              / sum(row["chars"] for row in reads)) if reads else 0.0,
            "followed": {"references/protocol.md", "references/worker.md"} <= {row["file"].split(KICK_OFF)[-1] for row in reads},
            "turns": len(turns), "cost": result.get("total_cost_usd") or 0.0}


def records():
    return [json.loads(path.read_text()) for path in sorted(RECORDS.glob("*.json"))] if RECORDS.exists() else []


def counted():
    """Each record with its recount, those without a sound stream left out."""
    rows = []
    for record in records():
        found = recount(record)
        if found:
            rows.append({**record, **found})
    return rows


def spent():
    return PRIOR_SPEND + sum(record.get("cost") or 0.0 for record in records())


def run_all(repeats, limit, parallel, arms, chosen):
    numbers = chosen or list(TASK_NUMBERS)
    todo = [(number, arm, repeat) for repeat in range(1, repeats + 1) for number in numbers for arm in (arms or arm_names())
            if not record_path(number, arm, repeat).exists()]
    with concurrent.futures.ThreadPoolExecutor(parallel) as pool:
        running = []
        for job in todo:
            while len(running) >= parallel:
                done, pending = concurrent.futures.wait(running, return_when=concurrent.futures.FIRST_COMPLETED)
                running = list(pending)
            if spent() + float(BUDGET) * (len(running) + 1) > limit:
                print(f"stop: ${spent():.2f} spent; another run could pass ${limit:.0f}")
                break
            running.append(pool.submit(run_one, *job))
        concurrent.futures.wait(running)
    print(f"spent ${spent():.2f}")
    return 0


def per_task(rows, arm, field):
    return {task: statistics.mean(row[field] for row in rows if row["arm"] == arm and row["task"] == task and row["followed"])
            for task in {row["task"] for row in rows if row["arm"] == arm and row["followed"]}}


def arm_figures(rows, arm):
    """Runs, passes, means, and the estimated saving: per task, the kick-off characters `none` opened beyond this run's, priced at
    the carry this run's own reads cost per character, over this run's bill. The bill changes with luck of the run, so the
    observed paired change in it is kept apart as `observed`."""
    here, base = [row for row in rows if row["arm"] == arm], [row for row in rows if row["arm"] == "none"]
    opened_by_task = per_task(rows, "none", "opened")
    bills, bases = per_task(rows, arm, "bill"), per_task(rows, "none", "bill")
    common = sorted(set(bills) & set(bases))
    followed = {row["task"] for row in base if row["followed"]}
    # a run that skipped protocol.md or worker.md opens fewer characters for no design's sake, so only runs that read both count
    estimates = [(opened_by_task[row["task"]] - row["opened"]) * row["unit_per_char"] / row["bill"]
                 for row in here if row["followed"] and row["task"] in followed]
    return {"runs": len(here), "passed": sum(row["passed"] for row in here),
            "bill": statistics.mean(row["bill"] for row in here) if here else None,
            "cost": statistics.mean(row["cost"] for row in here) if here else None,
            "opened": statistics.mean(row["opened"] for row in here) if here else None,
            "saving": statistics.mean(estimates) if estimates else None,
            "observed": statistics.mean((bases[task] - bills[task]) / bases[task] for task in common) if common else None}


def summary():
    rows = counted()
    print("| arm | runs | passed | mean bill | mean cost $ | mean kick-off characters opened | estimated saving | observed bill change |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for arm in arm_names():
        fig = arm_figures(rows, arm)
        if fig["runs"]:
            print(f"| {arm} | {fig['runs']} | {fig['passed']} | {fig['bill']:,.0f} | {fig['cost']:.3f} | {fig['opened']:,.0f} | "
                  f"{'' if fig['saving'] is None or arm == 'none' else format(fig['saving'], '.2%')} | "
                  f"{'' if fig['observed'] is None or arm == 'none' else format(fig['observed'], '.2%')} |")
    print(f"spent ${spent():.2f} of ${LIMIT:.0f}")
    return 0


def plan_time():
    """The commit time of the first `REPORTED: replay plan` comment on the issue naming a run count and a dollar cost."""
    log = subprocess.run(["git", "-C", str(ROOT), "log", "--reverse", "--format=%H %aI", "--diff-filter=A", "refs/teamwork-blackboard",
                          "--", f"teamwork/{ISSUE}/comments"], capture_output=True, text=True).stdout.splitlines()
    for line in log:
        sha, stamp = line.split()
        for name in subprocess.run(["git", "-C", str(ROOT), "ls-tree", "--name-only", "-r", sha, f"teamwork/{ISSUE}/comments"],
                                   capture_output=True, text=True).stdout.split():
            text = subprocess.run(["git", "-C", str(ROOT), "show", f"{sha}:{name}"], capture_output=True, text=True).stdout
            if text.startswith("REPORTED: replay plan") and re.search(r"\b\d+ runs\b", text) and re.search(r"\$\d", text):
                return stamp
    return None


def full_arms(rows):
    """The arms with every task run, `none` among them."""
    return [arm for arm in arm_names() if all(
        sum(1 for row in rows if row["arm"] == arm and row["task"] == number) >= REPEATS for number in TASK_NUMBERS)]


def check_designs():
    rows = counted()
    arms = full_arms(rows)
    if "none" not in arms or len(arms) < 2:
        return "FAIL: arm none and one other need every task run"
    if len(rows) != len(records()) or not all(row["clean"] for row in rows):
        return "FAIL: a run has no sound stream or is not clean"
    if any(any(check["result"] not in ("pass", "fail") for check in row["checks"]) or not row["checks"] for row in rows):
        return "FAIL: a run lacks its checks' verdicts"
    stamp = plan_time()
    if not stamp:
        return "FAIL: no replay plan comment"
    if min(row["started"] for row in rows)[:19] < utc(stamp):
        return "FAIL: a run began before the plan"
    return "PASS"


def utc(stamp):
    """STAMP, an ISO time with an offset, as `YYYY-MM-DDTHH:MM:SS` in UTC."""
    return datetime.datetime.fromisoformat(stamp).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def check_shipped():
    rows = counted()
    if len(rows) != len(records()) or not all(row["clean"] for row in rows):
        return "FAIL: a run has no sound stream or is not clean"
    head = head_hash()
    shipped = [row for row in rows if row["arm"] == "shipped" and row["tree"] == head]
    if not shipped or spent() > LIMIT:
        return "FAIL: no shipped run of this tree, or over the limit"
    fig, base = arm_figures(rows, "shipped"), arm_figures(rows, "none")
    if fig["runs"] != len(shipped) or fig["passed"] / fig["runs"] < base["passed"] / base["runs"]:
        return "FAIL: shipped passes a smaller share than none"
    if not fig["opened"] < base["opened"] or (fig["saving"] or 0) < MIN_GAIN:
        return "FAIL: shipped opens no fewer kick-off characters or saves under 1%"
    for arm in set(full_arms(rows)) - {"none", "shipped"}:
        other = arm_figures(rows, arm)
        if other["passed"] / other["runs"] >= base["passed"] / base["runs"] and (other["saving"] or 0) > fig["saving"]:
            return f"FAIL: arm {arm} saves more than shipped"
    return "PASS"


def main(args):
    if args == ["--list-arms"]:
        print(",".join(arm_names()))
        return 0
    if len(args) == 3 and args[0] == "--pilot":
        return run_one(args[1], args[2], 0, keep=False)
    if len(args) == 4 and args[0] == "--run":
        return run_one(*args[1:])
    if args and args[0] in ("--run-all", "--count-runs"):
        options, rest = {"--repeats": "1", "--max-dollars": str(LIMIT), "--parallel": "2", "--arms": "none,shipped", "--tasks": ""}, args[1:]
        while rest:
            if rest[0] not in options or len(rest) < 2:
                print(__doc__, file=sys.stderr)
                return 2
            options[rest[0]], rest = rest[1], rest[2:]
        arms = [arm for arm in options["--arms"].split(",") if arm]
        if args[0] == "--count-runs":
            print(int(options["--repeats"]) * len(TASK_NUMBERS) * len(arms or arm_names()))
            return 0
        return run_all(int(options["--repeats"]), float(options["--max-dollars"]), int(options["--parallel"]), arms,
                       [int(number) for number in options["--tasks"].split(",") if number])
    if args == ["--summary"]:
        return summary()
    if args == ["--check-designs"]:
        print(check_designs())
        return 0
    if args == ["--check-shipped"]:
        print(check_shipped())
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""usage: compare-team-output.py [--ref <ref>] [--only <entry>]

Run teamwork's entry points (hooks, board, heartbeat) in the current checkout and in an export of REF (default
origin/main) at the same time, against the live GitHub and herdr, and print `same` when every output matches,
else one unified diff per entry that differs. The manager is teamwork-manager, the worker protocol-split-worker."""
import argparse
import concurrent.futures as cf
import difflib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

TITLE = "x" * 45
EVENTS = {
    "manager-start": ("teamwork-manager", {"hook_event_name": "SessionStart", "session_id": ""}),
    "worker-start": ("protocol-split-worker", {"hook_event_name": "SessionStart", "session_id": ""}),
    "worker-stop": ("protocol-split-worker", {"hook_event_name": "Stop", "stop_hook_active": False, "transcript_path": ""}),
}
COMMANDS = ['gh issue create --title "x" --body-file f.md', "gh issue comment 1 --body hi", "gh issue comment 1 --body-file f.md",
            "gh issue edit 1 --body-file f.md", f'gh pr create --title "{TITLE}" --body-file f.md', "gh pr comment 1 --body-file f.md",
            "gh api -X POST repos/o/r/issues/1/comments -F body=@f.md", "gh api -X PATCH repos/o/r/issues/1 -f state=closed",
            "gh issue close 1 --reason completed", 'gh pr edit 1 --title "y"', "ls"]
for n, c in enumerate(COMMANDS):
    EVENTS[f"pre-{n}"] = ("protocol-split-worker", {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": c}, "cwd": "."})


def panes():
    listed = json.loads(subprocess.run(["herdr", "agent", "list"], capture_output=True, text=True).stdout)["result"]["agents"]
    return {a.get("name"): a["pane_id"] for a in listed if a.get("name")}


def run(tree, argv, pane=None, stdin=None, seconds=120):
    env = {**os.environ, **({"HERDR_PANE_ID": pane} if pane else {}), "MONITOR_POLL": "1000"}
    p = subprocess.Popen([str(tree / argv[0]), *argv[1:]], cwd=CWD, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    try:
        out, _ = p.communicate(stdin, timeout=seconds)
    except subprocess.TimeoutExpired:  # the heartbeat runs until killed
        p.kill()
        out, _ = p.communicate()
    return out.replace(str(tree), "<root>")


def outputs(tree, ids):
    jobs = {name: (["teamwork/hooks/route-event.py"], ids[who], json.dumps(e), 60) for name, (who, e) in EVENTS.items()}
    jobs["board"] = (["teamwork/hooks/list-issue-board.py", "teamwork"], None, None, 120)
    jobs["board-json"] = (["teamwork/hooks/list-issue-board.py", "teamwork", "--json"], None, None, 120)
    jobs["heartbeat"] = (["teamwork/monitors/print-team-gaps.py"], ids["teamwork-manager"], None, 100)
    S = "teamwork/skills/kick-off/scripts/"
    jobs["recall"] = ([S + "recall-work.py", "protocol adapter", "--path", "teamwork/lib/team_gaps.py"], None, None, 120)
    jobs["criteria"] = ([S + "run-criteria.py", "855"], None, None, 120)
    jobs["estimate"] = ([S + "estimate-task-time.py", "--seed", "1", "https://github.com/kalaluthien/mumu-claude-plugin/issues/852"], None, None, 180)
    jobs["durations"] = ([S + "list-task-durations.py", "kalaluthien/mumu-claude-plugin"], None, None, 300)
    jobs["edit-missing"] = ([S + "edit-issue-body.py", "999999", str(pathlib.Path(__file__).parent / "edit-probe.diff"), "DECIDED: probe"], None, None, 60)
    if ONLY:
        jobs = {k: v for k, v in jobs.items() if k.startswith(tuple(ONLY.split(",")))}
    with cf.ThreadPoolExecutor(8) as pool:
        futures = {k: pool.submit(run, tree, *v) for k, v in jobs.items()}
        return {k: f.result() for k, f in futures.items()}


parser = argparse.ArgumentParser()
parser.add_argument("--ref", default="origin/main")
parser.add_argument("--only", default="")
a = parser.parse_args()
ONLY = a.only
CWD = pathlib.Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or ".")
base = pathlib.Path(tempfile.mkdtemp(prefix="compare-team-")).resolve()
archive = subprocess.Popen(["git", "archive", a.ref, "teamwork"], stdout=subprocess.PIPE)
subprocess.run(["tar", "-x", "-C", str(base)], stdin=archive.stdout, check=True)
ids = panes()
with cf.ThreadPoolExecutor(2) as pool:
    here, there = pool.submit(outputs, CWD, ids), pool.submit(outputs, base, ids)
    here, there = here.result(), there.result()
differ = [k for k in here if here[k] != there[k]]
for k in differ:
    sys.stdout.writelines(difflib.unified_diff(there[k].splitlines(True), here[k].splitlines(True), f"{a.ref}:{k}", f"head:{k}"))
print(f"{len(here)} entries, empty: {' '.join(k for k in here if not here[k].strip()) or 'none'}")
print("same" if not differ else f"differ: {' '.join(differ)}")

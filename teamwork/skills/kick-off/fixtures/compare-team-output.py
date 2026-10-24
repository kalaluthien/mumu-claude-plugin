#!/usr/bin/env python3
"""usage: compare-team-output.py [--ref <ref>] [--only <entry>,...] [--skip <entry>,...] [--sandbox]

Run teamwork's entry points (hooks, board, heartbeat, scripts) in this checkout and in an export of REF (default
origin/main) at the same time, against the live herdr and GitHub, and print the entries, those with no output, then
`same` when every output matches, else one unified diff per entry that differs and `differ: <entries>`. The manager is
teamwork-manager, the worker protocol-split-worker. `--sandbox` reads kalaluthien/teamwork-board-sandbox instead, whose
fixture issues and one merged change give every entry output, and adds `edit-write`, which edits its issue #6 (base) or #7 (head) forward and
back. `--only` keeps the entries whose names start with one of its words, `--skip` drops them."""
import argparse
import concurrent.futures as cf
import difflib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SANDBOX = "kalaluthien/teamwork-board-sandbox"
EDIT_ISSUE = {"base": "6", "head": "7"}
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
K = "teamwork/skills/kick-off/scripts/"


def panes():
    listed = json.loads(subprocess.run(["herdr", "agent", "list"], capture_output=True, text=True).stdout)["result"]["agents"]
    return {a.get("name"): a["pane_id"] for a in listed if a.get("name")}


def run(tree, argv, pane=None, stdin=None, seconds=120, cwd=None, board=True):
    env = {**os.environ, **({"HERDR_PANE_ID": pane} if pane else {}), **({"GH_REPO": SANDBOX} if SAND and board else {}), "MONITOR_POLL": "1000"}
    argv = [str(tree / a) if a.startswith("teamwork/") else a for a in argv]
    p = subprocess.Popen(argv, cwd=cwd or ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        out, _ = p.communicate(stdin, timeout=seconds)
    except subprocess.TimeoutExpired:  # the heartbeat runs until killed
        p.kill()
        out, _ = p.communicate()
    # a reminder cites the rule's file and line, which the split moves; the rule's text is what must stay
    return re.sub(r"kick-off/[\w/.-]+:\d+: ", "kick-off/<file>: ", out.replace(str(tree), "<root>"))


def edit_write(tree, side):
    """The two lines edit-issue-body.py prints when it edits the sandbox issue forward, then back."""
    diffs = {}
    for name, a, b in (("forward", "before", "after"), ("back", "after", "before")):
        diffs[name] = pathlib.Path(tempfile.mkstemp(suffix=".diff")[1])
        diffs[name].write_text(f"--- a\n+++ b\n@@ -3 +3 @@\n-probe: {a}\n+probe: {b}\n")
    out = "".join(run(tree, [K + "edit-issue-body.py", EDIT_ISSUE[side], str(diffs[d]), f"DECIDED: probe {d}"]) for d in ("forward", "back"))
    return "\n".join(re.findall(r"edit-issue-body: .*", out)).replace(f"#{EDIT_ISSUE[side]}", "#<issue>")


def remove(tree):
    """What remove-worktree.py prints for a name with no worktree or branch, in a throwaway clone, so the live checkout is never pulled."""
    clone = pathlib.Path(tempfile.mkdtemp(prefix="remove-probe-"))
    try:
        subprocess.run(["git", "clone", "-q", "--shared", str(ROOT), str(clone)], check=True)
        url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        subprocess.run(["git", "remote", "set-url", "origin", url], cwd=clone, check=True)
        subprocess.run(["git", "fetch", "-q", "origin"], cwd=clone)
        subprocess.run(["git", "remote", "set-head", "origin", "--auto"], cwd=clone, capture_output=True)
        return run(tree, [K + "remove-worktree.py", "nobody-probe-worker"], cwd=clone)
    finally:
        shutil.rmtree(clone, ignore_errors=True)


def outputs(tree, side, ids):
    jobs = {name: (["teamwork/hooks/route-event.py"], ids.get(who), json.dumps(e), 60) for name, (who, e) in EVENTS.items()}
    jobs["board"] = (["teamwork/hooks/list-issue-board.py", "teamwork"], None, None, 120)
    jobs["board-json"] = (["teamwork/hooks/list-issue-board.py", "teamwork", "--json"], None, None, 120)
    jobs["heartbeat"] = (["teamwork/monitors/print-team-gaps.py"], ids.get("teamwork-manager"), None, 45)
    jobs["worker-heartbeat"] = (["teamwork/monitors/print-team-gaps.py"], ids.get("protocol-split-worker"), None, 45)
    jobs["recall"] = ([K + "recall-work.py", "protocol adapter", "--path", "./teamwork/lib/team_gaps.py"], None, None, 120)
    jobs["criteria"] = ([K + "run-criteria.py", "3" if SAND else "855"], None, None, 120)
    repo = SANDBOX if SAND else "kalaluthien/mumu-claude-plugin"  # the sandbox's one merged change closes its #5
    jobs["estimate"] = ([K + "estimate-task-time.py", "--seed", "1", f"https://github.com/{repo}/issues/{3 if SAND else 852}"], None, None, 180, None, False)
    jobs["durations"] = ([K + "list-task-durations.py", repo], None, None, 300, None, False)
    jobs["edit-missing"] = ([K + "edit-issue-body.py", "999999", str(HERE / "edit-probe.diff"), "DECIDED: probe"], None, None, 60)
    keep = lambda k: (not ONLY or k.startswith(tuple(ONLY))) and not k.startswith(tuple(SKIP))
    with cf.ThreadPoolExecutor(8) as pool:
        futures = {k: pool.submit(run, tree, *v) for k, v in jobs.items() if keep(k)}
        if keep("remove"):
            futures["remove"] = pool.submit(remove, tree)
        if SAND and keep("edit-write"):
            futures["edit-write"] = pool.submit(edit_write, tree, side)
        return {k: f.result() for k, f in futures.items()}


parser = argparse.ArgumentParser()
parser.add_argument("--ref", default="origin/main")
parser.add_argument("--only", default="")
parser.add_argument("--skip", default="")
parser.add_argument("--sandbox", action="store_true")
a = parser.parse_args()
ONLY, SKIP, SAND = [w for w in a.only.split(",") if w], [w for w in a.skip.split(",") if w], a.sandbox
ROOT = pathlib.Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or ".")
base = pathlib.Path(tempfile.mkdtemp(prefix="compare-team-")).resolve()
archive = subprocess.Popen(["git", "archive", a.ref, "teamwork"], cwd=ROOT, stdout=subprocess.PIPE)
subprocess.run(["tar", "-x", "-C", str(base)], stdin=archive.stdout, check=True)
ids = panes()
with cf.ThreadPoolExecutor(2) as pool:
    here, there = pool.submit(outputs, ROOT, "head", ids), pool.submit(outputs, base, "base", ids)
    here, there = here.result(), there.result()
shutil.rmtree(base, ignore_errors=True)
differ = [k for k in here if here[k] != there[k]]
for k in differ:
    sys.stdout.writelines(difflib.unified_diff(there[k].splitlines(True), here[k].splitlines(True), f"{a.ref}:{k}", f"head:{k}"))
print(f"{len(here)} entries, empty: {' '.join(k for k in here if not here[k].strip()) or 'none'}")
print("same" if not differ else f"differ: {' '.join(differ)}")

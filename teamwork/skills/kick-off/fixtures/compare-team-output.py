#!/usr/bin/env python3
"""Run teamwork's entry points (hooks, board, heartbeat, scripts) in this checkout and in an export of REF (default
origin/main; on a branch, `"$(git merge-base HEAD origin/main)"`, since origin/main moves when another change merges and its diffs then read as yours) at the same time, against the board kalaluthien/teamwork-board-sandbox as the tape of recorded-gh/gh beside this file
holds it, while no judge or worker writes the same sandbox board (a failure then reads the other's writes as changes: rerun it once alone), and a fake herdr (fake-herdr/herdr beside this file) that lists the two sessions below, and print the entries,
those with no output, then `same` when every output matches, else one unified diff per entry that differs and `differ: <entries>`.

usage: compare-team-output.py [--ref <ref>] [--only <entry>,...] [--skip <entry>,...]
The manager is teamwork-manager, the worker protocol-split-worker. The sandbox's fixture issues and one merged change give every
entry output; `edit-write` edits its issue #6 (base) or #7 (head) forward and back.
`--only` keeps the entries whose names start with one of its words, `--skip` drops them."""
import concurrent.futures
import difflib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import usage_parser  # noqa: E402

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
for n, command in enumerate(COMMANDS):
    EVENTS[f"pre-{n}"] = ("protocol-split-worker", {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}, "cwd": "."})
# a holders line outside its fence, in a body file before the write and read back from the sandbox's #9 after it
EVENTS["stray-pre"] = ("protocol-split-worker", {"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": str(HERE),
                                                 "tool_input": {"command": "gh issue comment 1 --body-file stray-holders.md"}})
EVENTS["stray-post"] = ("protocol-split-worker", {"hook_event_name": "PostToolUse", "tool_name": "Bash", "cwd": ".",
                                                  "tool_input": {"command": "gh issue create --title x --body-file f.md"},
                                                  "tool_response": {"stdout": f"https://github.com/{SANDBOX}/issues/9\n"}})
SCRIPTS = "teamwork/skills/kick-off/scripts/"


SESSIONS = {"teamwork-manager": ("w1:p1", "idle"), "protocol-split-worker": ("w1:p2", "working")}


def fake_herdr(tree):
    """A state file of its own per tree, so the two trees' calls never meet."""
    state = pathlib.Path(tempfile.mkstemp(prefix="fake-herdr-", suffix=".json")[1])
    state.write_text(json.dumps({"n": 10, "tabs": [{"tab_id": f"w1:t{i}", "workspace_id": "w1", "label": name} for i, name in enumerate(SESSIONS, 1)],
                                 "agents": [{"name": name, "pane_id": pane, "tab_id": pane.replace(":p", ":t"), "workspace_id": "w1", "agent": "claude",
                                             "agent_status": status, "interactive_ready": True} for name, (pane, status) in SESSIONS.items()]}))
    return state


def github_env(tree):
    """What sends a tree's gh calls to the tape, each tree counting its own turns."""
    return {"PATH": f"{HERE / 'recorded-gh'}:{HERE / 'fake-herdr'}:{os.environ['PATH']}", "GH_TAPE": "compare-team-output", "GH_TAPE_STATE": str(STATES[tree]) + ".gh"}


def run(tree, argv, pane=None, stdin=None, seconds=120, cwd=None, board=True):
    env = {**os.environ, **({"HERDR_PANE_ID": pane} if pane else {}), **({"GH_REPO": SANDBOX} if board else {}), "MONITOR_POLL": "1000",
           **github_env(tree), "FAKE_HERDR_STATE": str(STATES[tree])}
    argv = [str(tree / argument) if argument.startswith("teamwork/") else argument for argument in argv]
    process = subprocess.Popen(argv, cwd=cwd or ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        out, _ = process.communicate(stdin, timeout=seconds)
    except subprocess.TimeoutExpired:  # the heartbeat runs until killed
        process.kill()
        out, _ = process.communicate()
    # a reminder cites the rule's file and line, which the split moves; the rule's text is what must stay
    return re.sub(r"kick-off/[\w/.-]+:\d+: ", "kick-off/<file>: ", out.replace(str(tree), "<root>"))


def edit_write(tree, side):
    """The two lines edit-issue-body.py prints when it edits the sandbox issue forward, then back."""
    diffs = {}
    for name, old, new in (("forward", "before", "after"), ("back", "after", "before")):
        diffs[name] = pathlib.Path(tempfile.mkstemp(suffix=".diff")[1])
        diffs[name].write_text(f"--- a\n+++ b\n@@ -3 +3 @@\n-probe: {old}\n+probe: {new}\n")
    out = "".join(run(tree, [SCRIPTS + "edit-issue-body.py", EDIT_ISSUE[side], str(diffs[direction]), f"DECIDED: probe {direction}"]) for direction in ("forward", "back"))
    for comment in set(re.findall(rf"(?:repos/{SANDBOX}/issues/comments/|{SANDBOX}/issues/\d+#issuecomment-)(\d+)", out)):  # so the issue does not grow a comment pair per run
        subprocess.run(["gh", "api", "-X", "DELETE", f"repos/{SANDBOX}/issues/comments/{comment}"], capture_output=True, env={**os.environ, **github_env(tree)})
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
        return run(tree, [SCRIPTS + "remove-worktree.py", "nobody-probe-worker"], cwd=clone)
    finally:
        shutil.rmtree(clone, ignore_errors=True)


def outputs(tree, side, ids):
    jobs = {name: (["teamwork/hooks/route-event.py"], ids.get(who), json.dumps(event), 60) for name, (who, event) in EVENTS.items()}
    jobs["board"] = (["teamwork/hooks/list-issue-board.py", "teamwork"], None, None, 120)
    jobs["board-json"] = (["teamwork/hooks/list-issue-board.py", "teamwork", "--json"], None, None, 120)
    jobs["heartbeat"] = (["teamwork/monitors/print-team-gaps.py"], ids.get("teamwork-manager"), None, 45)
    jobs["worker-heartbeat"] = (["teamwork/monitors/print-team-gaps.py"], ids.get("protocol-split-worker"), None, 45)
    jobs["recall"] = ([SCRIPTS + "recall-work.py", "protocol adapter", "--path", "./teamwork/lib/team_gaps.py"], None, None, 120)
    jobs["criteria"] = ([SCRIPTS + "run-criteria.py", "3"], None, None, 120)
    # the sandbox's one merged change closes its #5
    jobs["estimate"] = ([SCRIPTS + "estimate-task-time.py", "--seed", "1", f"https://github.com/{SANDBOX}/issues/3"], None, None, 180, None, False)
    jobs["durations"] = ([SCRIPTS + "list-task-durations.py", SANDBOX], None, None, 300, None, False)
    jobs["edit-missing"] = ([SCRIPTS + "edit-issue-body.py", "999999", str(HERE / "edit-probe.diff"), "DECIDED: probe"], None, None, 60)
    keep = lambda k: (not ONLY or k.startswith(tuple(ONLY))) and not k.startswith(tuple(SKIP))
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        futures = {k: pool.submit(run, tree, *job) for k, job in jobs.items() if keep(k)}
        if keep("remove"):
            futures["remove"] = pool.submit(remove, tree)
        if keep("edit-write"):
            futures["edit-write"] = pool.submit(edit_write, tree, side)
        return {k: future.result() for k, future in futures.items()}


def main(args):
    global ONLY, SKIP, ROOT, STATES
    parser = usage_parser.parser(__doc__)
    parser.add_argument("--ref", default="origin/main")
    parser.add_argument("--only", default="")
    parser.add_argument("--skip", default="")
    options = parser.parse_args(args)
    ONLY, SKIP = [word for word in options.only.split(",") if word], [word for word in options.skip.split(",") if word]
    ROOT = pathlib.Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or ".")
    base = pathlib.Path(tempfile.mkdtemp(prefix="compare-team-")).resolve()
    archive = subprocess.Popen(["git", "archive", options.ref, "teamwork"], cwd=ROOT, stdout=subprocess.PIPE)
    subprocess.run(["tar", "-x", "-C", str(base)], stdin=archive.stdout, check=True)
    ids = {name: pane for name, (pane, _) in SESSIONS.items()}
    STATES = {ROOT: fake_herdr(ROOT), base: fake_herdr(base)}
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        here, there = pool.submit(outputs, ROOT, "head", ids), pool.submit(outputs, base, "base", ids)
        here, there = here.result(), there.result()
    shutil.rmtree(base, ignore_errors=True)
    for state in STATES.values():
        pathlib.Path(f"{state}.gh").unlink(missing_ok=True)
    differ = [k for k in here if here[k] != there[k]]
    for k in differ:
        sys.stdout.writelines(difflib.unified_diff(there[k].splitlines(True), here[k].splitlines(True), f"{options.ref}:{k}", f"head:{k}"))
    print(f"{len(here)} entries, empty: {' '.join(k for k in here if not here[k].strip()) or 'none'}")
    print("same" if not differ else f"differ: {' '.join(differ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

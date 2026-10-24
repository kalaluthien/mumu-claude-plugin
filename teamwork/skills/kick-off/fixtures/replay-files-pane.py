#!/usr/bin/env python3
"""Check that the issue pane draws a files board as it draws the same issues from GitHub: file a backlog with an open held task, a task waiting on it, a
completed task and a not-planned one through use-board.py, then compare list-issue-board.py's lines on the files board with its lines on GitHub-shaped nodes
written here by hand. Prints `ok pane` and exits 0, else the two outputs and exit 1.

usage: replay-files-pane.py"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
USE = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
LIST = ROOT / "hooks" / "list-issue-board.py"
HOLD = "## Goal\n\nProbe {n}.\n\n```teamwork\nholders: probe-worker\n```\n\n## Definition of done\n\n1. [check] **probe passes**: `echo ok` prints `ok`; on base nothing.\n"
PLAIN = "## Goal\n\nProbe {n}.\n\n## Definition of done\n\n1. [check] **probe passes**: `echo ok` prints `ok`; on base nothing.\n"
BODIES = {1: "Probe the pane by a backlog.\n", 2: HOLD.format(n=2), 3: PLAIN.format(n=3), 4: PLAIN.format(n=4), 5: PLAIN.format(n=5)}
TITLES = {1: "Probe the pane backlog", 2: "Probe the held task", 3: "Probe the waiting task", 4: "Probe the done task", 5: "Probe the stopped task"}


def node(number, **more):
    labels = [{"name": "backlog"}] if number == 1 else []
    return {"number": number, "title": TITLES[number], "url": f"https://github.com/o/r/issues/{number}", "body": BODIES[number], "authorAssociation": "OWNER",
            "parent": {"number": 1} if number > 1 else None, "labels": {"nodes": labels}, "subIssuesSummary": {"total": 0, "completed": 0},
            "subIssues": {"nodes": []}, "blockedBy": {"nodes": []}, "comments": {"nodes": []}, **more}


def github_nodes():
    """What GitHub's read gives for the issues filed below: the open ones as nodes, the closed ones only under their backlog."""
    sub = lambda n, state, reason, **more: {"number": n, "title": TITLES[n], "url": f"https://github.com/o/r/issues/{n}", "state": state, "stateReason": reason,
                                            "authorAssociation": "OWNER", **more}
    backlog = node(1, subIssuesSummary={"total": 4, "completed": 2}, subIssues={"nodes": [
        sub(2, "OPEN", None), sub(3, "OPEN", None), sub(4, "CLOSED", "COMPLETED", blockedBy={"nodes": []}), sub(5, "CLOSED", "NOT_PLANNED", blockedBy={"nodes": []})]})
    return [backlog, node(2), node(3, blockedBy={"nodes": [{"number": 2, "state": "OPEN"}]})]


def main(args):
    work = pathlib.Path(tempfile.mkdtemp(prefix="files-pane-"))
    env = {**os.environ, "TEAMWORK_BOARD": "files", "TEAMWORK_BOARD_DIR": str(work / "board"), "HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "home")}
    use = lambda *argv: subprocess.run([sys.executable, str(USE), *map(str, argv)], env=env, capture_output=True, text=True, check=True).stdout
    for number in BODIES:
        (work / f"{number}.md").write_text(BODIES[number])
        use("file", TITLES[number], work / f"{number}.md", *(["backlog"] if number == 1 else []))
        if number > 1:
            use("nest", 1, number)
    use("order", 3, 2)
    for number, flag in ((4, []), (5, ["--not-planned"])):
        (work / "done.md").write_text("REPORTED: probe done\n")
        use("resolve", number, work / "done.md", *flag)
    files = subprocess.run([sys.executable, str(LIST), "x"], env=env, capture_output=True, text=True)
    (work / "nodes.json").write_text(json.dumps(github_nodes()))
    github = subprocess.run([sys.executable, str(LIST), "--nodes", str(work / "nodes.json")], env={**env, "TEAMWORK_BOARD": "github"}, capture_output=True, text=True)
    if files.returncode or github.returncode or files.stdout != github.stdout or "closed stopped" not in files.stdout:
        print(f"files board:\n{files.stdout}{files.stderr}\ngithub nodes:\n{github.stdout}{github.stderr}")
        return 1
    print("ok pane")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

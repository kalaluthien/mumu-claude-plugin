#!/usr/bin/env python3
"""Replay a board written before its records were named `task.json`, in a temporary repository: a commit of `<n>/issue.json` records
put straight on `refs/teamwork-blackboard`, then the real scripts read it, list it for the pane and write to it, printing `ok <case>` or
`fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `read`: `use-board.py read` finds an old record's title, comment and holders;
- `pane`: `list-task-board.py --json` lists every old record of the project;
- `moved`: the first write, a `comment`, gives every record a `task.json` and leaves no `issue.json`, in one commit;
- `kept`: a record the write did not touch reads the same before and after it, and the commented one only adds the comment;
- `hold-first`: on a second old board whose first write is a `hold`, every record is moved and the new holder reads back;
- `both-names`: on a board the mirroring code left, each record in both names, a write removes every `issue.json` and keeps each `task.json`
  as it was, apart from the written record's own change.

usage: replay-board-move.py"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
USE = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
LIST = ROOT / "hooks" / "list-task-board.py"
REF = "refs/teamwork-blackboard"
failed = []


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {str(detail).strip()[:600]}", flush=True)
    if not ok:
        failed.append(name)


def record(title):
    return json.dumps({"title": title, "labels": [], "state": "OPEN", "reason": "", "createdAt": "2026-11-01T00:00:00Z", "closedAt": None,
                       "depends": [], "updatedAt": "2026-11-01T00:00:00Z"})


OLD_BOARD = {
    "probe/1/issue.json": record("Probe the part"),
    "probe/1/body.md": "## Goal\n\nProbe the part.\n",
    "probe/1/comments/0001.json": json.dumps({"text": "DECIDED: probe-worker holds this", "holders": ["probe-worker"]}),
    "probe/1/comments/0002.json": json.dumps({"text": "REPORTED: probe note"}),
    "probe/2/issue.json": record("Probe the parent"),
    "probe/2/body.md": "## Goal\n\nProbe the parent.\n\n## Definition of done\n\n1. [task] #1 Probe the part\n",
}


def old_board(work, name, board=OLD_BOARD):
    """A runner of commands in a new repository whose board is BOARD, committed straight on the ref."""
    environment = {**os.environ, "HOME": str(work), "CLAUDE_CONFIG_DIR": str(work / "claude"), "GIT_CONFIG_GLOBAL": str(work / "gitconfig")}
    repository = work / name
    (repository / "probe").mkdir(parents=True)
    (repository / "probe" / "a.txt").write_text("base\n")

    def sh(*argv, data=None):
        return subprocess.run([*map(str, argv)], cwd=repository, env=environment, capture_output=True, text=True, input=data, timeout=120)

    for command in (["git", "init", "-q"], ["git", "add", "-A"], ["git", "commit", "-q", "-m", "base"]):
        sh(*command)
    index = {**environment, "GIT_INDEX_FILE": str(work / f"{name}-index")}
    subprocess.run(["git", "read-tree", "--empty"], cwd=repository, env=index, check=True)
    for path, text in board.items():
        blob = subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=repository, env=index, input=text, capture_output=True, text=True, check=True).stdout.strip()
        subprocess.run(["git", "update-index", "--add", "--cacheinfo", f"100644,{blob},{path}"], cwd=repository, env=index, check=True)
    tree = subprocess.run(["git", "write-tree"], cwd=repository, env=index, capture_output=True, text=True, check=True).stdout.strip()
    commit = subprocess.run(["git", "commit-tree", tree, "-m", "old board"], cwd=repository, env=index, capture_output=True, text=True, check=True).stdout.strip()
    sh("git", "update-ref", REF, commit)
    return sh


def files(sh):
    return {path: sh("git", "show", f"{REF}:{path}").stdout for path in sh("git", "ls-tree", "-r", "--name-only", REF).stdout.split()}


def moved(board):
    return sorted(path for path in board if path.endswith(".json") and "/comments/" not in path) == ["probe/1/task.json", "probe/2/task.json"]


def commits(sh):
    return int(sh("git", "rev-list", "--count", REF).stdout.strip())


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="board-move-"))
    (work / "gitconfig").write_text("[user]\n\tname = probe\n\temail = probe@example.com\n[init]\n\tdefaultBranch = main\n")
    sh = old_board(work, "repo")
    one, two = sh(sys.executable, USE, "read", "1"), sh(sys.executable, USE, "read", "2")
    step("read", one.returncode == 0 and "Probe the part" in one.stdout and "probe note" in one.stdout and "probe-worker" in one.stdout, one.stdout + one.stderr)
    pane = sh(sys.executable, LIST, "probe", "--json")
    rows = json.loads(pane.stdout) if pane.returncode == 0 and pane.stdout.startswith("[") else []
    step("pane", sorted(row["number"] for row in rows) == [1, 2], pane.stdout + pane.stderr)
    count = commits(sh)
    wrote = sh(sys.executable, USE, "comment", "2", "--reported", "probe second note")
    board = files(sh)
    step("moved", wrote.returncode == 0 and commits(sh) == count + 1 and moved(board), f"{wrote.stderr} {sorted(board)}")
    after_one, after_two = sh(sys.executable, USE, "read", "1").stdout, sh(sys.executable, USE, "read", "2").stdout
    lost = [line for line in two.stdout.split("\n") if line not in after_two.split("\n") and not line.startswith("body sha")]
    step("kept", after_one == one.stdout and "probe second note" in after_two and not lost, f"{one.stdout}\n---\n{after_one}\n---\nlost: {lost}")
    sh = old_board(work, "held")
    wrote = sh(sys.executable, USE, "hold", "1", "--holders", "other-worker")
    read = sh(sys.executable, USE, "read", "1")
    step("hold-first", wrote.returncode == 0 and moved(files(sh)) and "holders: other-worker" in read.stdout, wrote.stderr + read.stdout)
    both = {**OLD_BOARD, "probe/1/task.json": record("Probe the part, renamed"), "probe/2/task.json": record("Probe the parent")}
    sh = old_board(work, "both", both)
    wrote = sh(sys.executable, USE, "comment", "2", "--reported", "probe second note")
    board = files(sh)
    step("both-names", wrote.returncode == 0 and moved(board) and board["probe/1/task.json"] == both["probe/1/task.json"]
         and json.loads(board["probe/2/task.json"])["title"] == "Probe the parent", f"{wrote.stderr} {sorted(board)}")
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

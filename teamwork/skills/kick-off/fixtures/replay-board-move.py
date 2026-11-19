#!/usr/bin/env python3
"""Replay a board written before its records were named `task.json`, in a temporary repository: a commit of `<n>/issue.json` records
put straight on `refs/teamwork-blackboard`, then the real scripts read it, list it for the pane and write to it, printing `ok <case>` or
`fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `read`: `use-board.py read` finds an old record's title, comment and holders;
- `pane`: `list-task-board.py --json` lists every old record of the project;
- `mirrored`: the first write, a `comment`, gives every record a `task.json` and keeps each `issue.json` equal to it, in one commit, since a
  heartbeat started before the rename reads only `issue.json`;
- `kept`: a record the write did not touch reads the same before and after it, and the commented one only adds the comment;
- `hold-first`: on a second old board whose first write is a `hold`, every record gets its `task.json` and the new holder reads back;
- `old-after-new`: a write as the code before the rename makes it, to `issue.json` alone, after the new code's writes, is what the new reader
  and the pane lister show, and the next new write keeps it in both names;
- `same-second`: an older session's write in the same second as the new code's last write, which leaves the two names differing, is
  what the new reader shows;
- `old-signal`: `wait-team-change.py` wakes on a mark of `issues-changed` alone, the one a session started before the rename makes.

usage: replay-board-move.py"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
USE = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
LIST = ROOT / "hooks" / "list-task-board.py"
WAIT = ROOT / "hooks" / "wait-team-change.py"
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


def old_board(work, name):
    """A runner of commands in a new repository whose board is OLD_BOARD, committed straight on the ref."""
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
    for path, text in OLD_BOARD.items():
        blob = subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=repository, env=index, input=text, capture_output=True, text=True, check=True).stdout.strip()
        subprocess.run(["git", "update-index", "--add", "--cacheinfo", f"100644,{blob},{path}"], cwd=repository, env=index, check=True)
    tree = subprocess.run(["git", "write-tree"], cwd=repository, env=index, capture_output=True, text=True, check=True).stdout.strip()
    commit = subprocess.run(["git", "commit-tree", tree, "-m", "old board"], cwd=repository, env=index, capture_output=True, text=True, check=True).stdout.strip()
    sh("git", "update-ref", REF, commit)
    return sh


def old_write(sh, path, text):
    """Commits TEXT at PATH on the board's tip, as the code before the rename writes `issue.json`."""
    index = {**os.environ, "GIT_INDEX_FILE": sh("git", "rev-parse", "--absolute-git-dir").stdout.strip() + "/old-write-index"}
    top = sh("git", "rev-parse", "--show-toplevel").stdout.strip()
    git = lambda *argv, data=None: subprocess.run(["git", *argv], cwd=top, env=index, input=data, capture_output=True, text=True, check=True).stdout.strip()
    git("read-tree", REF)
    git("update-index", "--add", "--cacheinfo", f"100644,{git('hash-object', '-w', '--stdin', data=text)},{path}")
    commit = git("commit-tree", git("write-tree"), "-p", REF, "-m", "old write")
    sh("git", "update-ref", REF, commit)


def files(sh):
    return {path: sh("git", "show", f"{REF}:{path}").stdout for path in sh("git", "ls-tree", "-r", "--name-only", REF).stdout.split()}


def mirrored(board):
    records = [path for path in board if path.endswith("/task.json")]
    return len(records) == 2 and all(board.get(path[:-len("task.json")] + "issue.json") == board[path] for path in records)


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
    note = work / "note.md"
    note.write_text("REPORTED: probe second note\n")
    count = commits(sh)
    wrote = sh(sys.executable, USE, "comment", "2", note)
    board = files(sh)
    step("mirrored", wrote.returncode == 0 and commits(sh) == count + 1 and mirrored(board), f"{wrote.stderr} {sorted(board)}")
    after_one, after_two = sh(sys.executable, USE, "read", "1").stdout, sh(sys.executable, USE, "read", "2").stdout
    lost = [line for line in two.stdout.split("\n") if line not in after_two.split("\n") and not line.startswith("body sha")]
    step("kept", after_one == one.stdout and "probe second note" in after_two and not lost, f"{one.stdout}\n---\n{after_one}\n---\nlost: {lost}")
    sh = old_board(work, "held")
    wrote = sh(sys.executable, USE, "hold", "1", "other-worker")
    read = sh(sys.executable, USE, "read", "1")
    step("hold-first", wrote.returncode == 0 and mirrored(files(sh)) and "holders: other-worker" in read.stdout, wrote.stderr + read.stdout)
    closed = json.loads(files(sh)["probe/1/issue.json"])
    old_write(sh, "probe/1/issue.json", json.dumps({**closed, "state": "CLOSED", "reason": "COMPLETED", "updatedAt": "2099-01-01T00:00:00Z"}))
    read = sh(sys.executable, USE, "read", "1")
    pane = sh(sys.executable, LIST, "probe", "--json")
    open_rows = [row["number"] for row in json.loads(pane.stdout)] if pane.stdout.startswith("[") else None
    wrote = sh(sys.executable, USE, "comment", "1", note)
    board = files(sh)
    step("old-after-new", "state: CLOSED" in read.stdout and open_rows is not None and 1 not in open_rows and wrote.returncode == 0
         and json.loads(board["probe/1/task.json"])["state"] == "CLOSED" and board["probe/1/task.json"] == board["probe/1/issue.json"],
         f"{read.stdout[:200]} {pane.stdout[:200]} {pane.stderr[:200]} {wrote.stderr}")
    same = json.loads(files(sh)["probe/1/task.json"])
    old_write(sh, "probe/1/issue.json", json.dumps({**same, "labels": ["oldlabel"]}))
    read = sh(sys.executable, USE, "read", "1")
    step("same-second", "oldlabel" in read.stdout, read.stdout[:300])
    environment = {**os.environ, "CLAUDE_CONFIG_DIR": str(work / "claude")}
    waiter = subprocess.Popen([sys.executable, str(WAIT)], env=environment, stdout=subprocess.PIPE, text=True)
    try:
        first = waiter.stdout.readline()
        time.sleep(0.5)
        (work / "claude" / "teamwork" / "issues-changed").touch()
        deadline = time.time() + 10
        second = ""
        os.set_blocking(waiter.stdout.fileno(), False)
        while time.time() < deadline and not second:
            second = waiter.stdout.readline()
            time.sleep(0.2)
    finally:
        waiter.kill()
    step("old-signal", first.strip() == "changed" and second.strip() == "changed", f"{first!r} {second!r}")
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

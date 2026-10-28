#!/usr/bin/env python3
"""Nest tasks through use-board.py on a temporary files board and print `ok <case>`, or `fail <case>: <what it read>`:
`under-task`, a task nested under another task lands on their backlog; `no-backlog`, a task nested under an issue with no backlog
at or above it is refused and keeps no parent.

usage: replay-nest-target.py"""
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
USE = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"


def use(*argv):
    return subprocess.run([sys.executable, str(USE), *map(str, argv)], capture_output=True, text=True)


def filed(title, *labels):
    body = pathlib.Path(tempfile.mkstemp(suffix=".md")[1])
    body.write_text(f"{title}.\n")
    return use("file", title, body, *labels).stdout.strip().rsplit("/", 1)[1]


def parent(number):
    return next(line.split(": ", 1)[1] for line in use("read", number).stdout.splitlines() if line.startswith("parent: "))


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {detail.strip()}", flush=True)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    os.environ.update(TEAMWORK_BOARD="files", TEAMWORK_BOARD_DIR=tempfile.mkdtemp(prefix="nest-board-"))
    backlog, task, follow_up = filed("Backlog", "backlog"), filed("Task"), filed("Follow-up")
    use("nest", backlog, task)
    nested = use("nest", task, follow_up)
    read = parent(follow_up)
    step("under-task", nested.returncode == 0 and read == backlog, f"parent {read}, {nested.stderr}")
    loose, orphan = filed("Loose"), filed("Orphan")
    refused = use("nest", loose, orphan)
    read = parent(orphan)
    step("no-backlog", refused.returncode == 1 and read == "None", f"exit {refused.returncode}, parent {read}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

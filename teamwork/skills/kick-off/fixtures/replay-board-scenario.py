#!/usr/bin/env python3
"""usage: replay-board-scenario.py --board <github|files>

File a backlog and a task, nest and order them, set holders, ask by BLOCKED, answer by DECIDED, edit the body and resolve both, writing only through
use-board.py, and print after each step a `step <name>` line, the composed state of each issue it filed and the board lines, numbers and urls replaced
by names, so two boards that print the same text keep the same protocol. The files board runs in a temporary folder. The github board runs on the
repository `GH_REPO` names, never this one, since its issues would reach the team's board: with `GH_REPO` unset or naming it, the run calls no gh,
prints `not a sandbox` and exits 1."""
import argparse
import difflib
import os
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
USE = HERE.parent / "scripts" / "use-board.py"
THIS_REPO = "kalaluthien/mumu-claude-plugin"
parser = argparse.ArgumentParser()
parser.add_argument("--board", choices=("github", "files"), required=True)
board_name = parser.parse_args().board
work = pathlib.Path(tempfile.mkdtemp(prefix="board-scenario-"))
os.environ["TEAMWORK_BOARD"] = board_name
if board_name == "github" and (os.environ.get("GH_REPO") or THIS_REPO) == THIS_REPO:
    sys.exit("replay-board-scenario: not a sandbox: set GH_REPO to a repository whose issues the team's board never reads")
if board_name == "files":
    os.environ["TEAMWORK_BOARD_DIR"], os.environ["HOME"] = str(work / "board"), str(work)  # so the signal file is the scenario's own too
sys.path.insert(0, str(HERE.parents[2] / "lib"))
import board  # noqa: E402
import issue_board  # noqa: E402
import issue_state  # noqa: E402

names = {}  # the number each issue got, by the name the output uses


def use(*argv):
    return subprocess.run([sys.executable, str(USE), *map(str, argv)], capture_output=True, text=True, check=True).stdout.strip()


def text(name, body):
    path = work / name
    path.write_text(body)
    return path


def filed(name, title, body, labels=()):
    names[int(use("file", title, text(name, body), *labels).rsplit("/", 1)[1])] = name


def number(name):
    return next(n for n, v in names.items() if v == name)


def plain(out):
    """OUT with each url one word and each issue number its name."""
    return re.sub(r"#(\d+)", lambda m: "#" + names.get(int(m.group(1)), m.group(1)), re.sub(r"(?:https|file)://\S+", "<url>", out))


def show(step):
    print(f"step {step}")
    for n, name in sorted(names.items(), key=lambda x: x[1]):
        r = board.fresh(n)
        s = issue_state.compose(r, board.blockers(n))
        parent = names.get(r["parent"])
        criteria = [(d["kind"], d["name"], bool(d["met"])) for d in s["done"]]
        print(plain(f"{name}: {r['state']} labels={sorted(r['labels'])} parent={parent} holders={s['holders']} waits={s['waits']} comments={len(r['comments'])} criteria={criteria}"))
    nodes = board.tree(None)
    if nodes is None:
        sys.exit("replay-board-scenario: the board read failed")
    print(plain("\n".join(issue_board.lines(issue_board.board([n for n in nodes if n["number"] in names])))))


TASK = "## Goal\n\nProbe the board.\n\n## Definition of done\n\n1. [check] **probe passes**: `echo ok` prints `ok`; on base nothing.\n"
filed("backlog", "Probe the board backlog", "Probe the board by a backlog.\n", ["backlog"])
filed("task", "Probe the board task", TASK)
show("file")
use("nest", number("backlog"), number("task"))
show("nest")
use("order", number("backlog"), number("task"))
show("order")
use("decide", number("task"), text("hold.md", "DECIDED: probe-worker holds this.\n\n```teamwork\nholders: probe-worker\n```\n"))
show("hold")
use("label", number("task"), "probe")
show("label-add")
use("label", number("task"), "probe", "--remove")
show("label-remove")
use("comment", number("task"), text("ask.md", "BLOCKED: which sample proves the probe\n\nOptions:\n1. **ok**: the first\n2. **no**: the second\n\n```teamwork\nasks: owner\n```\n"))
show("ask")
use("decide", number("task"), text("answer.md", "DECIDED: owner said: use the first\n\n- Answers the ask above: option 1.\n"))
show("answer")
old = board.fresh(number("task"))["body"]
diff = "".join(difflib.unified_diff(old.splitlines(True), old.replace("Probe the board.", "Probe the board twice.").splitlines(True), "a", "b"))
use("edit", number("task"), text("edit.diff", diff), "DECIDED: probe the body edit")
show("edit")
use("resolve", number("task"), text("task-done.md", "REPORTED: probe landed\n"))
show("resolve-task")
use("resolve", number("backlog"), text("backlog-done.md", "REPORTED: probe landed\n"))
show("resolve-backlog")

#!/usr/bin/env python3
"""File a root and a task, make the task the root's part and the root wait on it by body edits, set holders, ask by BLOCKED, answer by DECIDED, edit the
body and resolve the task, which closes the root, then retitle and reopen the root, add a follow-up part to it and resolve that, which closes the root again, writing only through use-board.py, and print after each step a `step <name>` line, the composed state of each issue it filed and the board lines, numbers and urls replaced
by names, so a change that moves the protocol shows in the text. The board is a temporary repository.

usage: replay-board-scenario.py"""
import difflib
import os
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
USE = HERE.parent / "scripts" / "use-board.py"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import usage_parser  # noqa: E402

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
    return next(issue_number for issue_number, known in names.items() if known == name)


def plain(out):
    """OUT with each url one word and each issue number its name."""
    return re.sub(r"#(\d+)", lambda match: "#" + names.get(int(match.group(1)), match.group(1)), re.sub(r"(?:https|(?:git\+)?file)://\S+", "<url>", out))


def show(step):
    print(f"step {step}")
    for issue_number, name in sorted(names.items(), key=lambda item: item[1]):
        record = board.fresh(issue_number)
        state = issue_state.compose(record, board.blockers(issue_number))
        parent = names.get(record["parent"])
        criteria = [(criterion["kind"], criterion["name"], bool(criterion["met"])) for criterion in state["done"]]
        print(plain(f"{name}: {record['state']} labels={sorted(record['labels'])} parent={parent} holders={state['holders']} waits={state['waits']} comments={len(record['comments'])} criteria={criteria}"))
    nodes = board.tree(None)
    if nodes is None:
        sys.exit("replay-board-scenario: the board read failed")
    print(plain("\n".join(issue_board.lines(issue_board.board([node for node in nodes if node["number"] in names])))))


def link(name, added, why):
    """Appends ADDED to NAME's body by a diff through `use-board.py edit`, the one way a link is written."""
    old = board.fresh(number(name))["body"]
    diff = "".join(difflib.unified_diff(old.splitlines(True), (old.rstrip("\n") + "\n" + added).splitlines(True), "a", "b"))
    use("edit", number(name), text(f"{name}-link.diff", diff), f"DECIDED: {why}", "--base", board.body_sha(old))


TASK = "## Goal\n\nProbe the board.\n\n## Definition of done\n\n1. [check] **The probe prints PASS when it runs**: `echo ok` prints `ok`; on base nothing.\n"


def main(args):
    global work, board, issue_board, issue_state
    usage_parser.parser(__doc__).parse_args(args)
    work = pathlib.Path(tempfile.mkdtemp(prefix="board-scenario-"))
    subprocess.run(["git", "init", "-q", str(work / "repo")], check=True)
    os.chdir(work / "repo")
    os.environ["HOME"] = str(work)
    # imported here, since they read the board and folder set above when they load
    import board
    import issue_board
    import issue_state

    filed("root", "Probe the board root", "Probe the board by a root.\n")
    filed("task", "Probe the board task", TASK)
    show("file")
    link("root", f"\n## Definition of done\n\n1. [task] #{number('task')} Probe the board task\n", "the task is the root's part")
    show("part")
    link("root", f"\n```teamwork\ndepends on: #{number('task')}\n```\n", "the root waits on its task")
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
    use("edit", number("task"), text("edit.diff", diff), "DECIDED: probe the body edit", "--base", board.body_sha(old))
    show("edit")
    use("resolve", number("task"), text("task-done.md", "REPORTED: probe landed\n"))
    show("resolve-task")
    use("title", number("root"), "Probe the board again")
    show("retitle")
    use("reopen", number("root"))
    show("reopen")
    filed("follow-up", "Probe the board follow-up", TASK)
    link("root", f"2. [task] #{number('follow-up')} Probe the board follow-up\n", "a follow-up part")
    show("part-again")
    use("resolve", number("follow-up"), text("follow-up-done.md", "REPORTED: follow-up landed\n"))
    show("resolve-again")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

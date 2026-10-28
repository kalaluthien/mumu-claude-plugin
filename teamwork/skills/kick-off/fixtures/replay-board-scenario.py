#!/usr/bin/env python3
"""File a backlog and a task, nest and order them, set holders, ask by BLOCKED, answer by DECIDED, edit the body and resolve both, then retitle and
reopen the backlog, nest a follow-up task under it and resolve both again, writing only through use-board.py, and print after each step a `step <name>` line, the composed state of each issue it filed and the board lines, numbers and urls replaced
by names, so two boards that print the same text keep the same protocol. The files board runs in a temporary folder. The github board runs on the
repository `GH_REPO` names, as the tape of recorded-gh/gh beside this file holds it, while no judge or worker writes it (else rerun a failure once alone), never this one, since its issues would reach the team's board:
with `GH_REPO` unset or naming it, the run calls no gh, prints `not a sandbox` and exits 1.

usage: replay-board-scenario.py --board <github|files>"""
import difflib
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
USE = HERE.parent / "scripts" / "use-board.py"
THIS_REPO = "kalaluthien/mumu-claude-plugin"
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
    return re.sub(r"#(\d+)", lambda match: "#" + names.get(int(match.group(1)), match.group(1)), re.sub(r"(?:https|file)://\S+", "<url>", out))


def show(step):
    print(f"step {step}")
    for issue_number, name in sorted(names.items(), key=lambda item: item[1]):
        record = board.fresh(issue_number)
        state = issue_state.compose(record, board.blockers(issue_number))
        parent = names.get(record["parent"])
        criteria = [(criterion["kind"], criterion["name"], bool(criterion["met"])) for criterion in state["done"]]
        print(plain(f"{name}: {record['state']} labels={sorted(record['labels'])} parent={parent} holders={state['holders']} waits={state['waits']} comments={len(record['comments'])} criteria={criteria}"))
    closed = sum(board.fresh(issue_number, comments=False)["state"] == "CLOSED" for issue_number, known in names.items() if known != "backlog")
    for _ in range(15):  # GitHub counts a parent's closed sub-issues a moment after the close, so read until the count agrees
        nodes = board.tree(None)
        if nodes is None:
            sys.exit("replay-board-scenario: the board read failed")
        counts = [node["subIssuesSummary"]["completed"] for node in nodes if node["number"] == number("backlog")]
        if counts in ([], [closed]):
            break
        time.sleep(2)
    print(plain("\n".join(issue_board.lines(issue_board.board([node for node in nodes if node["number"] in names])))))


TASK = "## Goal\n\nProbe the board.\n\n## Definition of done\n\n1. [check] **probe passes**: `echo ok` prints `ok`; on base nothing.\n"


def main(args):
    global work, board, issue_board, issue_state
    parser = usage_parser.parser(__doc__)
    parser.add_argument("--board", choices=("github", "files"), required=True)
    board_name = parser.parse_args(args).board
    work = pathlib.Path(tempfile.mkdtemp(prefix="board-scenario-"))
    os.environ["TEAMWORK_BOARD"] = board_name
    if board_name == "github" and (os.environ.get("GH_REPO") or THIS_REPO) == THIS_REPO:
        sys.exit("replay-board-scenario: not a sandbox: set GH_REPO to a repository whose issues the team's board never reads")
    if board_name == "files":
        os.environ["TEAMWORK_BOARD_DIR"], os.environ["HOME"] = str(work / "board"), str(work)  # so the signal file is the scenario's own too
    else:  # each run filing issues on GitHub grew the sandbox and spent its rate limit
        os.environ.update({"PATH": f"{HERE / 'recorded-gh'}:{os.environ['PATH']}", "GH_TAPE": "replay-board-scenario", "GH_TAPE_STATE": str(work / "gh-turns.json")})
    # imported here, since they read the board and folder set above when they load
    import board
    import issue_board
    import issue_state

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
    use("title", number("backlog"), "Probe the board again")
    show("retitle")
    use("reopen", number("backlog"))
    show("reopen")
    filed("follow-up", "Probe the board follow-up", TASK)
    use("nest", number("backlog"), number("follow-up"))
    show("nest-again")
    use("resolve", number("follow-up"), text("follow-up-done.md", "REPORTED: follow-up landed\n"))
    use("resolve", number("backlog"), text("backlog-again.md", "REPORTED: follow-up landed\n"))
    show("resolve-again")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

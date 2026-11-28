#!/usr/bin/env python3
"""Print the project's open tasks as the task pane draws them: each part under its parent by a guide, a row's title with
`(blocked by #a #b)` while a blocker is open, then its status (`n/m parts done holder wait`), then what the pane folds under it: open questions, decisions, next step, criteria, closed parts.

usage: list-task-board.py <project> [--json [--width <n>] | --width <n> | --check] [--repository <folder>]
       list-task-board.py --nodes <file> [--json [--width <n>] | --width <n> | --check]
`--json` prints the rows the pane draws, laid out for `--width` cells, else for a narrow docked pane; `--width` alone wraps the
text to that many cells; `--check` prints per width 24, 30, 40, 60 and 80 whether the rows fit; `--nodes` reads the board's
task nodes from a file instead of the board; `--repository` names the checkout, main or worktree, whose board is read, else the current folder's."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import board  # noqa: E402
import data_folder  # noqa: E402
import session  # noqa: E402
import task_board  # noqa: E402


def main(args):
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    args = data_folder.enter(args, __doc__)
    width = args[args.index("--width") + 1] if "--width" in args and args.index("--width") + 1 < len(args) else None
    # kept --nodes as a seam: the pane's replays feed task nodes from a file, not the board
    words = [word for word in args if word not in ("--json", "--nodes", "--check", "--width", width)]  # kept --check until #1573
    if len(words) != 1 or words[0].startswith("-") or "--width" in args and not (width or "").isdigit():
        print(__doc__, file=sys.stderr)
        return 2
    read = board.tree(None, json.loads(pathlib.Path(words[0]).read_text())) if "--nodes" in args else board.tree(words[0])
    if read is None:
        sys.exit("list-task-board: the git board read failed, so no board is shown")
    tree = task_board.board(read, None if "--nodes" in args else session.live_names())
    if "--json" in args:
        laid = int(width) if width else task_board.PANE_WIDTH
        print(json.dumps([{**row, "lines": task_board.heading(row, laid)} for row in task_board.rows(tree, laid)]))
    elif "--check" in args:
        print("\n".join(task_board.check(tree)))
    else:
        print("\n".join(task_board.lines(tree, width and int(width))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

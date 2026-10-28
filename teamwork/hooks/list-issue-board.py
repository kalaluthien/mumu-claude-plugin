#!/usr/bin/env python3
"""Print the project's open issues as the issue pane draws them: backlogs grouped with related ones, each task under its
backlog by number, an entry's link line then its holder and wait, a task's goal and criteria, a backlog's progress and its closed tasks.

usage: list-issue-board.py <project> [--json]
       list-issue-board.py --nodes <file> [--json]
`--json` prints the same tree for the pane; `--nodes` reads the board's issue nodes from a file instead of the board."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import board  # noqa: E402
import issue_board  # noqa: E402


def main(args):
    words = [word for word in args if word not in ("--json", "--nodes")]
    if len(words) != 1 or words[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    read = board.tree(None, json.loads(pathlib.Path(words[0]).read_text())) if "--nodes" in args else board.tree(words[0])
    if read is None:
        sys.exit(f"list-issue-board: the {board.kind()} board read failed, so no board is shown")
    tree = issue_board.board(read)
    print(json.dumps(tree) if "--json" in args else "\n".join(issue_board.lines(tree)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""usage: list-issue-board.py <project> [--json] | --nodes <file> [--json]

Print the project's open issues as the issue pane draws them: backlogs grouped with related ones, each task under its
backlog by number, an entry's link line then its holder and wait, a task's goal and criteria, a backlog's progress and its closed tasks.
`--json` prints the same tree for the pane; `--nodes` reads the board's issue nodes from a file instead of the board."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import board  # noqa: E402
import issue_board  # noqa: E402

read = board.tree(None, json.loads(pathlib.Path(sys.argv[sys.argv.index("--nodes") + 1]).read_text())) if "--nodes" in sys.argv else board.tree(sys.argv[1])
if read is None:
    sys.exit("list-issue-board: a GitHub read failed, so no board is shown")
tree = issue_board.board(read)
print(json.dumps(tree) if "--json" in sys.argv else "\n".join(issue_board.lines(tree)))

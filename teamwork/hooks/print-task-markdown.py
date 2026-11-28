#!/usr/bin/env python3
"""Print one task as Markdown, the text the task pane draws when a task's number is pressed: its title, state, body, then each comment after a rule.

usage: print-task-markdown.py <number> [--repository <folder>]
       print-task-markdown.py --nodes <file> <number>
`--nodes` reads the task from the task nodes in a file instead of the board; `--repository` names the checkout, main or worktree, whose board is read, else the current folder's."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import board  # noqa: E402
import data_folder  # noqa: E402
import record_types  # noqa: E402


def main(args):
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    args = data_folder.enter(args, __doc__)
    nodes = None
    if any(argument.startswith("--") for argument in args[1:]):
        print(__doc__, file=sys.stderr)
        return 2
    if args[:1] == ["--nodes"] and len(args) == 3:
        nodes, args = json.loads(pathlib.Path(args[1]).read_text()), args[2:]
    if len(args) != 1 or not args[0].isdigit():
        print(__doc__, file=sys.stderr)
        return 2
    if nodes is None:
        task = board.fresh(args[0])
    else:
        found = next((node for node in nodes if node["number"] == int(args[0])), None)
        task = found and {**found, "state": found.get("state", "open"), "comments": found["comments"]["nodes"]}
    if not task:
        print(f"print-task-markdown: cannot read #{args[0]}", file=sys.stderr)
        return 1
    print(f"# #{task['number']} {task['title']}\n\n{task['state']}\n\n{task['body'].strip()}")
    for note in task["comments"]:
        judge = note["fields"].get("judge_note")
        print(f"\n---\n\n{record_types.shown(note).strip()}" + (f"\n\nJudge note: {judge}" if judge else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Print one task as Markdown, the text the issue pane draws when a task's number is pressed: its title, state, body, then each comment after a rule.

usage: print-task-markdown.py <number>
       print-task-markdown.py --nodes <file> <number>
`--nodes` reads the task from the issue nodes in a file instead of the board."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import board  # noqa: E402
import issue_state  # noqa: E402


def main(args):
    nodes = None
    if args[:1] == ["--nodes"] and len(args) == 3:
        nodes, args = json.loads(pathlib.Path(args[1]).read_text()), args[2:]
    if len(args) != 1 or not args[0].isdigit():
        print(__doc__, file=sys.stderr)
        return 2
    if nodes is None:
        issue = board.fresh(args[0])
    else:
        found = next((node for node in nodes if node["number"] == int(args[0])), None)
        issue = found and {**found, "trusted": True, "state": found.get("state", "OPEN"), "comments": [{"body": note["body"]} for note in found["comments"]["nodes"]]}
    if not issue:
        print(f"print-task-markdown: cannot read #{args[0]}", file=sys.stderr)
        return 1
    print(f"# #{issue['number']} {issue_state.title(issue)}\n\n{issue['state'].lower()}\n\n{issue['body'].strip()}")
    for note in issue["comments"]:
        print(f"\n---\n\n{note['body'].strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

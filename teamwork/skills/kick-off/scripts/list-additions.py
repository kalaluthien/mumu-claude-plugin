#!/usr/bin/env python3
"""Print the owner's decisions on a task that no body edit has folded in yet, and the body's sha, so a worker folds every addition in one edit.
A body edit folds a decision when its keyword line names the decision's url; exit 1 when the board read failed.

usage: list-additions.py <issue>"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board  # noqa: E402
import decisions  # noqa: E402
import issue_state  # noqa: E402


def main(args):
    number = decisions.task_number(args[0]) if len(args) == 1 else None
    if number is None:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        issues = decisions.read(number, board.fresh)
    except LookupError as e:
        print(f"list-additions: {e}, so nothing is listed", file=sys.stderr)
        return 1
    issue = issues[number]
    edit_lines = [comment["body"].lstrip().split("\n", 1)[0] for comment in issue["comments"] if "```diff" in comment["body"]]
    added = [d for d in decisions.binding(number, issues) if d["task"] == number and d["role"] == "owner"
             and not any(re.search(re.escape(d["url"]) + r"(?!\w)", line) for line in edit_lines)]
    body_sha = board.body_sha(issue["body"])
    print(f"#{number} body sha: {body_sha}")
    print(f"owner additions not in the body: {len(added)}")
    for decision in added:
        print(f"- {decision['decision']} ({decision['url']})")
    if added:
        print(f'fold them in one edit: use-board.py edit {number} <diff-file> "{issue_state.WORD["answer"]}: folds {" ".join(d["url"] for d in added)}" --base {body_sha}')
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

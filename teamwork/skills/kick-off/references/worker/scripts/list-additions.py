#!/usr/bin/env python3
"""Print the owner's decisions on a task that no body edit has folded in yet, and the body's sha, so a worker folds every addition in one edit.
A body edit folds a decision when its keyword line names the decision's url; exit 1 when the board read failed.

usage: list-additions.py <task> [--repository <folder>]"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[5] / "lib"))
import board  # noqa: E402
import board_refs  # noqa: E402
import data_folder  # noqa: E402
import decisions  # noqa: E402


def main(args):
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    args = data_folder.enter(args, __doc__)
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        number = board_refs.TaskRef.parse(args[0]).number
    except board_refs.Refused as e:
        print(f"list-additions: {args[0]!r} {e}\n{__doc__}", file=sys.stderr)
        return 2
    try:
        tasks = decisions.read(number, board.fresh)
    except LookupError as e:
        print(f"list-additions: {e}, so nothing is listed", file=sys.stderr)
        return 1
    task = tasks[number]
    edit_lines = [comment["body"].lstrip().split("\n", 1)[0] for comment in task["comments"] if "```diff" in comment["body"]]
    folded = {board_refs.stored(found) for line in edit_lines for found in re.findall(r"git\+file://.*?#comment-\d+(?!\d)", line)}
    added = [d for d in decisions.binding(number, tasks) if d["task"] == number and d["role"] == "owner" and board_refs.stored(d["url"]) not in folded]
    body_sha = board.body_sha(task["body"])
    print(f"#{number} body sha: {body_sha}")
    print(f"owner additions not in the body: {len(added)}")
    for decision in added:
        print(f"- {decision['decision']} ({decision['url']})")
    if added:
        print(f'fold them in one edit: use-board.py edit {number} --body <file> --reason "folds {" ".join(d["url"] for d in added)}" --base {body_sha}')
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

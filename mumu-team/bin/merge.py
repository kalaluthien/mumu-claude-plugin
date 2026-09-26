#!/usr/bin/env python3
"""Squash-merge a pull request at the head a reviewer approved: the only merge path.

usage: merge.py <pr-url>, as a Bash call of its own. It reads the PR's head,
finds a comment or review whose first line is `APPROVED: <head>` (any case, the
colon optional, so `Approved <sha>` counts), and runs
`gh pr merge <pr-url> --squash --match-head-commit <head>`, so a head that moves
after the read is refused by GitHub. Exits non-zero with the reason otherwise.
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
from gh import gh  # noqa: E402

URL = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/pull/\d+")
APPROVAL = re.compile(r"approved:?\s+(\S+)", re.I)


def approved(pr):
    """Whether a comment or review of the PR opens with an approval of its head."""
    notes = (pr.get("comments") or []) + (pr.get("reviews") or [])
    first_lines = [n["body"].strip().splitlines()[0].strip() for n in notes if n["body"].strip()]
    return any((m := APPROVAL.fullmatch(line)) and m[1].lower() == pr["headRefOid"] for line in first_lines)


def main(args):
    if len(args) != 1 or not URL.fullmatch(args[0]):
        sys.exit("usage: merge.py <pr-url>, the PR's full https://github.com/<owner>/<repo>/pull/<n> url")
    url = args[0]
    try:
        pr = json.loads(gh("pr", "view", url, "--json", "headRefOid,comments,reviews"))
    except RuntimeError as e:
        sys.exit(f"merge.py: could not read {url}: {e}")
    head = pr["headRefOid"]
    if not approved(pr):
        sys.exit(f"merge.py: no comment or review opens with `APPROVED: {head}`; launch the reviewer at this head")
    try:
        print(gh("pr", "merge", url, "--squash", "--match-head-commit", head), end="")
    except RuntimeError as e:
        sys.exit(f"merge.py: {e}")


if __name__ == "__main__":
    main(sys.argv[1:])

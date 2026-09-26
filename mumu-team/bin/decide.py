#!/usr/bin/env python3
"""Post a lead's `DECIDED:` comment on an issue, with `--criteria` first replacing its `## Definition of done` by the file's lines.

usage: decide.py <issue-url> [--criteria <file>] < decision
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
from gh import gh  # noqa: E402

DONE = re.compile(r"^## Definition of done[ \t]*\n.*?(?=^## |\Z)", re.M | re.S)


def replace_criteria(body, criteria):
    """`body` with its `## Definition of done` section holding `criteria`, every other section unchanged."""
    section = f"## Definition of done\n\n{criteria.strip()}\n"
    if DONE.search(body):
        return DONE.sub(lambda m: section + ("\n" if m.end() < len(body) else ""), body, count=1)
    return body.rstrip("\n") + "\n\n" + section


def main(argv):
    if len(argv) not in (1, 3) or len(argv) == 3 and argv[1] != "--criteria":
        sys.exit("usage: decide.py <issue-url> [--criteria <file>] < decision")
    url = argv[0]
    decision = sys.stdin.read().strip()
    if not decision:
        sys.exit("decide.py: no decision on stdin")
    if not re.match(r"decided\b", decision, re.I):
        decision = "DECIDED: " + decision
    try:
        if len(argv) == 3:
            body = gh("issue", "view", url, "--json", "body", "-q", ".body")
            with open(argv[2]) as f:
                gh("issue", "edit", url, "--body-file", "-", stdin=replace_criteria(body, f.read()))
        print(gh("issue", "comment", url, "--body-file", "-", stdin=decision + "\n").strip())
    except RuntimeError as e:
        sys.exit(f"decide.py: {e}")


if __name__ == "__main__":
    main(sys.argv[1:])

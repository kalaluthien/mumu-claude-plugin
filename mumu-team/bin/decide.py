#!/usr/bin/env python3
"""Post a lead's `DECIDED:` comment on an issue and, when asked, replace its criteria in the same call.

usage: decide.py <issue-url> [--criteria <file>] < decision

The decision is read from stdin; the comment's first line opens `DECIDED:`,
added unless the text already opens with it. With `--criteria`, the body's
`## Definition of done` section, up to the next `## ` heading or the end, is
replaced by the file's lines first, and every other section (`## Goal`) is kept
as it was; a body with no such section gains one at the end. Exits non-zero
with the failing `gh` call's message, and posts no comment when the edit fails.
"""
import re
import subprocess
import sys

DONE = re.compile(r"^## Definition of done[ \t]*\n.*?(?=^## |\Z)", re.M | re.S)


def replace_criteria(body, criteria):
    """`body` with its `## Definition of done` section holding `criteria`, every other section unchanged."""
    section = f"## Definition of done\n\n{criteria.strip()}\n"
    if DONE.search(body):
        return DONE.sub(lambda m: section + ("\n" if m.end() < len(body) else ""), body, count=1)
    return body.rstrip("\n") + "\n\n" + section


def gh(*args, stdin=None):
    done = subprocess.run(["gh", *args], input=stdin, capture_output=True, text=True)
    if done.returncode:
        sys.exit(f"decide.py: gh {' '.join(args[:2])}: {done.stderr.strip()}")
    return done.stdout


def main(argv):
    if len(argv) not in (1, 3) or len(argv) == 3 and argv[1] != "--criteria":
        sys.exit("usage: decide.py <issue-url> [--criteria <file>] < decision")
    url = argv[0]
    decision = sys.stdin.read().strip()
    if not decision:
        sys.exit("decide.py: no decision on stdin")
    if len(argv) == 3:
        body = gh("issue", "view", url, "--json", "body", "-q", ".body")
        with open(argv[2]) as f:
            gh("issue", "edit", url, "--body-file", "-", stdin=replace_criteria(body, f.read()))
    if not re.match(r"decided\b", decision, re.I):
        decision = "DECIDED: " + decision
    print(gh("issue", "comment", url, "--body-file", "-", stdin=decision + "\n").strip())


if __name__ == "__main__":
    main(sys.argv[1:])

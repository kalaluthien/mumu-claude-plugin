#!/usr/bin/env python3
"""Print the model a pull request's `reviewer` runs on: `sonnet` for at most 20 changed lines, else `opus`.

usage: review-size.py <base> <head>, run in the checkout; the count is the
insertions plus deletions of `git diff --shortstat <base>...<head>`.
"""
import re
import subprocess
import sys

SMALL = 20


def changed(shortstat):
    """Insertions plus deletions in one `git diff --shortstat` line; an empty line is 0."""
    return sum(int(n) for n in re.findall(r"(\d+) (?:insertion|deletion)", shortstat))


def model_for(lines):
    return "sonnet" if lines <= SMALL else "opus"


def main():
    if len(sys.argv) != 3:
        print("usage: review-size.py <base> <head>", file=sys.stderr)
        return 2
    diff = subprocess.run(["git", "diff", "--shortstat", f"{sys.argv[1]}...{sys.argv[2]}"], capture_output=True, text=True)
    if diff.returncode != 0:
        print(f"review-size.py: {diff.stderr.strip()}", file=sys.stderr)
        return 2
    lines = changed(diff.stdout)
    print(f"{model_for(lines)} ({lines} changed lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

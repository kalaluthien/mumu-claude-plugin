#!/usr/bin/env python3
"""Print the model a pull request's `reviewer` runs on: `sonnet` for at most 20 changed lines, else `opus`.

usage: review-model.py <base> <head>, run in the checkout; the count is the
insertions plus deletions of `git diff --shortstat <base>...<head>`.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
from command import run  # noqa: E402

SMALL = 20


def changed(shortstat):
    """Insertions plus deletions in one `git diff --shortstat` line; an empty line is 0."""
    return sum(int(n) for n in re.findall(r"(\d+) (?:insertion|deletion)", shortstat))


def model_for(lines):
    return "sonnet" if lines <= SMALL else "opus"


def main():
    if len(sys.argv) != 3:
        print("usage: review-model.py <base> <head>", file=sys.stderr)
        return 2
    try:
        lines = changed(run("git", "diff", "--shortstat", f"{sys.argv[1]}...{sys.argv[2]}"))
    except RuntimeError as e:
        print(f"review-model.py: {e}", file=sys.stderr)
        return 2
    print(f"{model_for(lines)} ({lines} changed lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

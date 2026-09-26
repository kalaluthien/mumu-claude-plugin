#!/usr/bin/env python3
"""Print the `reviewer`'s model: `sonnet` for at most 20 changed lines, else `opus`.

usage: review-model.py <base> <head>, run in the checkout.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
from gh import run  # noqa: E402


def changed(shortstat):
    """Insertions plus deletions in one `git diff --shortstat` line; an empty line is 0."""
    return sum(int(n) for n in re.findall(r"(\d+) (?:insertion|deletion)", shortstat))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: review-model.py <base> <head>")
    try:
        lines = changed(run("git", "diff", "--shortstat", f"{sys.argv[1]}...{sys.argv[2]}"))
    except RuntimeError as e:
        sys.exit(f"review-model.py: {e}")
    print(f"{'sonnet' if lines <= 20 else 'opus'} ({lines} changed lines)")

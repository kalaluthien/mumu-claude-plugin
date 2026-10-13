#!/usr/bin/env python3
"""Raise a memory file's confirmation count when its lesson is found again.

  count-confirmations.py confirm <memory file>   raise `confirmed` by one and set
                                                 `last-confirmed` to today

Both fields sit in the file's frontmatter. `confirm` changes those two lines
only, in place at any indent (Claude Code nests them under `metadata:`),
adding them, or a frontmatter, when missing.
"""
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "lib"))
import memory  # noqa: E402


def confirm(path, today):
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    count, _ = memory.fields(path)
    front, body = memory.split(text)
    front = front if front is not None else ""
    for name, value in (("confirmed", str(count + 1)), ("last-confirmed", today.isoformat())):
        line = re.compile(rf"^([ \t]*){name}:.*$", re.M)
        front = line.sub(rf"\g<1>{name}: {value}", front) if line.search(front) else front + f"{name}: {value}\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(f"---\n{front}---\n{body}")
    print(f"{path}: confirmed {count + 1}, last-confirmed {today.isoformat()}")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "confirm":
        sys.exit(confirm(args[1], date.today()))
    print(__doc__.split("\n\n")[1], file=sys.stderr)
    sys.exit(2)

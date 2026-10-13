#!/usr/bin/env python3
"""Raise a memory file's confirmation count when its lesson is found again.

  count-confirmations.py <memory file>   raise `confirmed` by one and set
                                         `last-confirmed` to today

Both fields sit in the file's frontmatter. It changes those two lines
only, in place at any indent (Claude Code nests them under `metadata:`),
adding them, or a frontmatter, when missing.
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "lib"))
import memory  # noqa: E402


def confirm(path, today):
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    count, _ = memory.fields(path, text)
    front, body = memory.split(text)
    front = front or ""
    values = {"confirmed": str(count + 1), "last-confirmed": today.isoformat()}
    present = {name for _, name, _ in memory.FIELD.findall(front)}
    front = memory.FIELD.sub(lambda m: f"{m.group(1)}{m.group(2)}: {values[m.group(2)]}", front)
    front += "".join(f"{name}: {value}\n" for name, value in values.items() if name not in present)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(f"---\n{front}---\n{body}")
    print(f"{path}: confirmed {count + 1}, last-confirmed {today.isoformat()}")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 1:
        sys.exit(confirm(args[0], date.today()))
    print(__doc__.split("\n\n")[1], file=sys.stderr)
    sys.exit(2)

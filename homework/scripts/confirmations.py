#!/usr/bin/env python3
"""Count how often a memory file's lesson was found again, and list the lessons never found again.

  confirmations.py confirm <memory file>   raise its `confirmed` count by one and
                                           set `last-confirmed` to today
  confirmations.py stale <config> [<days>] list the memory files of
                                           <config>/projects/*/memory at
                                           `confirmed` 1 whose `last-confirmed`
                                           is over <days> (default 60) days old

Both fields sit in the file's frontmatter; a missing `confirmed` reads 1 and a
missing `last-confirmed` reads the file's modification date. `confirm` changes
those two lines only, in place at any indent (Claude Code nests them under
`metadata:`), adding them, or a frontmatter, when missing.
"""
import glob
import os
import re
import sys
from datetime import date, timedelta

FIELD = re.compile(r"^[ \t]*(confirmed|last-confirmed):[ \t]*(.*)$", re.M)


def split(text):
    """(frontmatter, body), frontmatter None when the file has none."""
    found = re.match(r"---\n(.*?\n)?---\n", text, re.S)
    return (found.group(1) or "", text[found.end():]) if found else (None, text)


def fields(path):
    with open(path, encoding="utf-8") as handle:
        front, _ = split(handle.read())
    values = dict(FIELD.findall(front or ""))
    try:
        count = int(values.get("confirmed", "1"))
    except ValueError:
        count = 1
    try:
        last = date.fromisoformat(values["last-confirmed"].strip())
    except (KeyError, ValueError):
        last = date.fromtimestamp(os.path.getmtime(path))
    return count, last


def confirm(path, today):
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    count, _ = fields(path)
    front, body = split(text)
    front = front if front is not None else ""
    for name, value in (("confirmed", str(count + 1)), ("last-confirmed", today.isoformat())):
        line = re.compile(rf"^([ \t]*){name}:.*$", re.M)
        front = line.sub(rf"\g<1>{name}: {value}", front) if line.search(front) else front + f"{name}: {value}\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(f"---\n{front}---\n{body}")
    print(f"{path}: confirmed {count + 1}, last-confirmed {today.isoformat()}")
    return 0


def stale(config, days, today):
    for path in sorted(glob.glob(os.path.join(glob.escape(config), "projects", "*", "memory", "*.md"))):
        if os.path.basename(path) == "MEMORY.md":
            continue
        count, last = fields(path)
        if count <= 1 and today - last > timedelta(days=days):
            with open(path, encoding="utf-8") as handle:
                lines = len(handle.read().splitlines())
            print(f"{path}: confirmed {count}, last-confirmed {last.isoformat()}; "
                  f"deleting it and its MEMORY.md line touches 2 files, {lines + 1} lines")
    return 0


if __name__ == "__main__":
    args, today = sys.argv[1:], date.today()
    if len(args) == 2 and args[0] == "confirm":
        sys.exit(confirm(args[1], today))
    if len(args) in (2, 3) and args[0] == "stale":
        sys.exit(stale(args[1], int(args[2]) if len(args) == 3 else 60, today))
    print(__doc__.split("\n\n")[1], file=sys.stderr)
    sys.exit(2)

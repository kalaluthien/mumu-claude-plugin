#!/usr/bin/env python3
"""Raise a memory file's confirmation count when its lesson is found again.

usage: count-confirmations.py <memory file>   raise `confirmed` by one and set
                                              `last-confirmed` to today

Both fields sit in the file's frontmatter. It changes those two lines
only, in place at any indent (Claude Code nests them under `metadata:`),
adding them, or a frontmatter, when missing.
"""
import pathlib
import sys
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import memory  # noqa: E402


def confirm(path, today):
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as error:
        print(f"could not confirm {path}: {error.strerror}", file=sys.stderr)
        return 1
    count, _ = memory.fields(path, text)
    front, body = memory.split(text)
    front = front or ""
    values = {"confirmed": str(count + 1), "last-confirmed": today.isoformat()}
    present = {name for _, name, _ in memory.FIELD.findall(front)}
    front = memory.FIELD.sub(lambda match: f"{match.group(1)}{match.group(2)}: {values[match.group(2)]}", front)
    front += "".join(f"{name}: {value}\n" for name, value in values.items() if name not in present)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(f"---\n{front}---\n{body}")
    print(f"{path}: confirmed {count + 1}, last-confirmed {today.isoformat()}")
    return 0


def main(args):
    if len(args) == 1 and not args[0].startswith("-"):
        return confirm(args[0], date.today())
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

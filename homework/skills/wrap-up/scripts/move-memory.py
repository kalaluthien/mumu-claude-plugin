#!/usr/bin/env python3
"""Move a memory file to another memory folder, such as from a repository's folder to the auto-memory home, with its index line.

usage: move-memory.py <memory file> <destination folder>

The file's line in its folder's `MEMORY.md` moves to the destination's `MEMORY.md`, which is made when missing; it refuses a
destination that already holds a file of that name, so no lesson is overwritten."""
import pathlib
import re
import sys

INDEX = "MEMORY.md"


def main(args):
    if len(args) != 2 or any(arg.startswith("-") for arg in args):
        print(__doc__, file=sys.stderr)
        return 2
    source, destination = pathlib.Path(args[0]), pathlib.Path(args[1])
    if not source.is_file() or source.name == INDEX:
        print(f"not moved: {source} is no memory file", file=sys.stderr)
        return 1
    if destination.exists() and not destination.is_dir():
        print(f"not moved: {destination} is no folder", file=sys.stderr)
        return 1
    target = destination / source.name
    if target.exists():
        print(f"not moved: {target} exists; merge the two by hand", file=sys.stderr)
        return 1
    # only the line whose own link is the file, so a line that mentions it in its text stays
    link = re.compile(rf"^\s*[-*] \[[^\]]*\]\({re.escape(source.name)}\)")
    source_index = source.parent / INDEX
    lines = source_index.read_text(encoding="utf-8").splitlines(keepends=True) if source_index.is_file() else []
    moved = [line for line in lines if link.match(line)]
    destination.mkdir(parents=True, exist_ok=True)
    source.rename(target)
    if moved:
        source_index.write_text("".join(line for line in lines if not link.match(line)), encoding="utf-8")
        destination_index = destination / INDEX
        before = destination_index.read_text(encoding="utf-8") if destination_index.is_file() else ""
        separator = "" if not before or before.endswith("\n") else "\n"
        destination_index.write_text(before + separator + "".join(line if line.endswith("\n") else line + "\n" for line in moved),
                                     encoding="utf-8")
        print(f"moved {source} to {target}, with its index line")
    else:
        print(f"moved {source} to {target}; {source_index} had no line for it, so add one to {destination / INDEX}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

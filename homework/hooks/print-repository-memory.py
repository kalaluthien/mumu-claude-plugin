#!/usr/bin/env python3
"""Print, as a session starts, where this repository's lessons go under the auto-memory home and the index of those already kept.

usage: print-repository-memory.py   a SessionStart hook; reads the event's JSON on stdin

It prints nothing when no `autoMemoryDirectory` is set, since the session then has a pool of its own, and always exits 0,
since a failure here must never stop a session from starting."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import memory_home  # noqa: E402

SENTENCE = ("Repository memory: a lesson true only for {repository} goes in {folder}/, one file each, its index line in "
            "{folder}/MEMORY.md; a lesson for every project goes in the auto-memory root, {root}/.")


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 0
    try:
        cwd = json.load(sys.stdin).get("cwd") or "."
    except (ValueError, AttributeError):
        cwd = "."
    root = memory_home.home(cwd)
    if not root:
        return 0
    repository = memory_home.repository(cwd)
    folder = root / repository
    print(SENTENCE.format(repository=repository, folder=folder, root=root))
    index = folder / "MEMORY.md"
    try:
        print(index.read_text(encoding="utf-8", errors="replace").rstrip())
    except OSError:
        print("It holds no lesson yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Print, as a session starts, that lessons go to the auto-memory home by default and the index of this repository's rare folder when it holds an entry.

usage: print-repository-memory.py   a SessionStart hook; reads the event's JSON on stdin

With no global `autoMemoryDirectory` it prints nothing, since the retro and dream scripts fail on their own when they need it.
It always exits 0, since a failure here must never stop a session from starting."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import memory  # noqa: E402
import memory_home  # noqa: E402

SENTENCE = ("Memory: a lesson goes in the auto-memory root, {root}/, one file each; only a lesson wrong or harmful outside "
            "{repository} goes in {folder}/, its index line in {folder}/MEMORY.md.")


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 0
    root = memory_home.home()
    if not root:
        return 0
    try:
        cwd = json.load(sys.stdin).get("cwd")
    except (ValueError, AttributeError):
        cwd = None
    cwd = cwd if isinstance(cwd, str) and cwd else "."
    repository = memory_home.repository(cwd)
    if not repository:
        return 0
    folder = root / repository
    print(SENTENCE.format(repository=repository, folder=folder, root=root))
    index = folder / "MEMORY.md"
    try:
        text = index.read_text(encoding="utf-8", errors="replace").rstrip()
    except OSError:
        return 0
    # a title alone holds no lesson, so printing it spends start-up context on nothing
    if memory.index_words(text):
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

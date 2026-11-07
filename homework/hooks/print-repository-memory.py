#!/usr/bin/env python3
"""Print, as a session starts, that lessons go to the auto-memory home by default and the index of this repository's rare folder when it holds an entry.

usage: print-repository-memory.py   a SessionStart hook; reads the event's JSON on stdin

When no `autoMemoryDirectory` is set, it prints only a `systemMessage` for the person, with the line to add to
`~/.claude/settings.json`, since the agent needs no word of it and a new machine would run on without the shared home
unnoticed; it never writes a settings file. It always exits 0, since a failure here must never stop a session from starting."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import memory  # noqa: E402
import memory_home  # noqa: E402

SENTENCE = ("Memory: a lesson goes in the auto-memory root, {root}/, one file each; only a lesson wrong or harmful outside "
            "{repository} goes in {folder}/, its index line in {folder}/MEMORY.md.")
WARNING = ("homework: `autoMemoryDirectory` is not set, so memory stays in each project's own pool. "
           "To share one memory home, add to ~/.claude/settings.json: {\"autoMemoryDirectory\": \"~/.claude/memory\"}")


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 0
    try:
        cwd = json.load(sys.stdin).get("cwd")
    except (ValueError, AttributeError):
        cwd = None
    cwd = cwd if isinstance(cwd, str) and cwd else "."
    root = memory_home.home(cwd)
    if not root:
        print(json.dumps({"systemMessage": WARNING}))
        return 0
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

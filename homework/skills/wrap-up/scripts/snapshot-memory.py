#!/usr/bin/env python3
"""Record the auto-memory home as a commit of its history, so a lesson a session or a tidy changes can be read and put back.

usage: snapshot-memory.py <config> <message> [--export <folder>]

The history is the bare git directory beside the home, `<home>.git`, where <home> is the `autoMemoryDirectory` of <config>'s `settings.json`.
It prints `snapshot <commit> <message>` for a changed home and `snapshot unchanged <commit>` for one that matches the last commit, and exits 0.
With `--export` it then writes the last commit's files to `<folder>/<home>`, the layout of the dream's backup, and prints `snapshot exported <n> files to <folder>/<home>`.
It prints `snapshot refused: <reason>` and exits 1 for an empty home, a repository inside the home, a surrounding repository that does not ignore `<home>.git`, or a failed git command or file write;
an unset `autoMemoryDirectory` exits 1 with the setting's name on stderr."""
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import memory_history  # noqa: E402
import memory_home  # noqa: E402


def main(args):
    if len(args) not in (2, 4) or (len(args) == 4 and args[2] != "--export") or any(arg.startswith("-") for arg in args[:2]):
        print(__doc__, file=sys.stderr)
        return 2
    config, message = args[:2]
    try:
        home = memory_home.require(config)
        commit, made = memory_history.snapshot(home, message)
        print(f"snapshot {commit[:10]} {message}" if made else f"snapshot unchanged {commit[:10]}")
        if len(args) == 4:
            count = memory_history.export(home, args[3])
            print(f"snapshot exported {count} files to {pathlib.Path(args[3]).absolute()}{pathlib.Path(home).absolute()}")
    except (memory_history.Refused, OSError, subprocess.SubprocessError) as refusal:
        print(f"snapshot refused: {refusal}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

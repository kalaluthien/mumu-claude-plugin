#!/usr/bin/env python3
"""Copy every record of one local board into another, verbatim and in one write, such as the files board into the git board before setting
`TEAMWORK_BOARD=git`; the copy keeps issue numbers, bodies and times, but each copied comment takes the time of the copy. Refuses a target that
already holds an issue, printing its numbers and exit 1, since a copy over it would mix two boards' numbers. Prints the count copied.

usage: copy-board.py <files|git> <files|git>"""
import importlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board_records  # noqa: E402

KINDS = ("files", "git")


def paths(store, folder=""):
    for name in store.children(folder):
        path = f"{folder}/{name}" if folder else name
        children = store.children(path)
        yield from paths(store, path) if children else [path]


def main(args):
    if len(args) != 2 or args[0] == args[1] or not set(args) <= set(KINDS):
        print(__doc__, file=sys.stderr)
        return 2
    source, target = (importlib.import_module(f"board_{kind}").STORE for kind in args)
    try:
        source.refresh()
        every = {path: source.read(path) for path in paths(source)}

        def change():
            held = board_records.numbers(target)
            if held:
                raise LookupError(f"the {args[1]} board already holds #{', #'.join(map(str, held))}: copy only into an empty board")
            for path, text in every.items():
                target.stage(path, text)
        target.write(change)
    except (OSError, LookupError) as e:
        print(f"copy-board: {e}", file=sys.stderr)
        return 1
    print(f"copied {len(board_records.numbers(source))} issues, {len(every)} files, from the {args[0]} board to the {args[1]} board")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

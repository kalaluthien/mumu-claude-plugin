#!/usr/bin/env python3
"""Copy every record of one board into another local board, verbatim and in one write, such as the files board into the git board before any other
write to it; the copy keeps issue numbers, bodies and times, but each comment copied between local boards takes the time of the copy. From `github` it copies
every issue, closed ones too, with each comment's GitHub time, skips a body or comment of an author the GitHub board does not trust, rewrites a GitHub issue or comment url in a text to
the target's url for that record, files an issue labelled `scope:<folder>` of a top-level folder under that folder and drops the label, and sets the target's number floor above the highest issue or pull-request number. Refuses a target that
already holds an issue, printing its numbers and exit 1, since a copy over it would mix two boards' numbers. Prints the count copied.

usage: copy-board.py <files|git|github> <files|git>"""
import importlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board_records  # noqa: E402
import github_copy  # noqa: E402

KINDS = ("files", "git")


def paths(store, folder=""):
    for name in store.children(folder):
        path = f"{folder}/{name}" if folder else name
        children = store.children(path)
        yield from paths(store, path) if children else [path]


def main(args):
    if len(args) != 2 or args[0] == args[1] or args[1] not in KINDS or args[0] not in (*KINDS, "github"):
        print(__doc__, file=sys.stderr)
        return 2
    target = importlib.import_module(f"board_{args[1]}").STORE
    try:
        if args[0] == "github":
            every, untrusted_issues, untrusted_comments = github_copy.files(*github_copy.read(), target)
            held = sum(1 for path in every if path.endswith("/issue.json") or path == "issue.json")
            print(f"skipped {untrusted_issues} issues and {untrusted_comments} comments of authors the GitHub board does not trust")
        else:
            source = importlib.import_module(f"board_{args[0]}").STORE
            source.refresh()
            every = {path: source.read(path) for path in paths(source)}
            held = len(board_records.numbers(source))

        def change():
            present = board_records.numbers(target)
            if present:
                raise LookupError(f"the {args[1]} board already holds #{', #'.join(map(str, present))}: copy only into an empty board")
            for path, text in every.items():
                target.stage(path, text)
        target.write(change)
    except (OSError, LookupError) as e:
        print(f"copy-board: {e}", file=sys.stderr)
        return 1
    print(f"copied {held} issues, {len(every)} files, from the {args[0]} board to the {args[1]} board")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

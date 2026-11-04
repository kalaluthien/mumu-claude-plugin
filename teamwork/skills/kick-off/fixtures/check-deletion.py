#!/usr/bin/env python3
"""Check that a deletion left nothing of what it removed: print each tracked file whose path matches a pattern and each line of another file that holds a word,
then `PASS` as the last line when none is left, else `FAIL` and exit 1. `--except` skips the paths it matches in both searches. `--shrink` instead prints the
tracked lines of the repository (the new files included) now and at a revision, then `PASS` when the plugin holds fewer than it did.

usage: check-deletion.py --files <regex> --words <regex> [--except <regex>]
       check-deletion.py --shrink <revision>
       check-deletion.py --count --files <regex> --words <regex> [--except <regex>]
`--count` prints the lines each matching file holds, which a deletion removes, and each line that holds a word, which it edits, then the totals."""
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=HERE, capture_output=True, text=True, check=True).stdout.strip())


def tracked(root=ROOT):
    """The paths git lists in the repository, new files included, that exist."""
    listed = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "."], cwd=root, capture_output=True, text=True, check=True).stdout
    return sorted(path for path in listed.split("\0") if path and (root / path).is_file())


def read(path):
    """A file's lines, or None for a binary one."""
    data = (ROOT / path).read_bytes()
    return None if b"\0" in data else data.decode("utf-8", "replace").splitlines()


def shrink(revision):
    now = sum(len(lines) for lines in map(read, tracked()) if lines)
    counted = subprocess.run(["git", "grep", "-I", "-c", "", revision, "--", "."], cwd=ROOT, capture_output=True, text=True)
    then = sum(int(row.rsplit(":", 1)[1]) for row in counted.stdout.splitlines())
    print(f"{revision}: {then} lines, now: {now} lines")
    return now < then


def main(args):
    options = {"--files": None, "--words": None, "--except": None, "--shrink": None}
    flags = {"--count"}
    count = False
    rest = list(args)
    while rest:
        flag = rest.pop(0)
        if flag in flags:
            count = True
        elif flag in options and rest and options[flag] is None:
            options[flag] = rest.pop(0)
        else:
            print(__doc__, file=sys.stderr)
            return 2
    if options["--shrink"]:
        if any(options[flag] for flag in ("--files", "--words", "--except")) or count:
            print(__doc__, file=sys.stderr)
            return 2
        done = shrink(options["--shrink"])
        print("PASS" if done else "FAIL")
        return 0 if done else 1
    if not options["--files"] and not options["--words"]:
        print(__doc__, file=sys.stderr)
        return 2
    skip = re.compile(options["--except"]) if options["--except"] else None
    files = re.compile(options["--files"]) if options["--files"] else None
    words = re.compile(options["--words"]) if options["--words"] else None
    removed = edited = left = 0
    for path in tracked():
        if skip and skip.search(path):
            continue
        lines = read(path)
        if files and files.search(path):
            held = len(lines or [])
            removed += held
            left += 1
            print(f"{path}: file, {held} lines")
        elif words and lines:
            for number, line in enumerate(lines, 1):
                if words.search(line):
                    edited += 1
                    left += 1
                    print(f"{path}:{number}: {line.strip()[:140]}")
    if count:
        print(f"removed with their files: {removed} lines; lines that hold a word: {edited}")
        return 0
    print("PASS" if not left else "FAIL")
    return 0 if not left else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

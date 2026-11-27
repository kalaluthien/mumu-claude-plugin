#!/usr/bin/env python3
"""Print the one check strategy playbook for the change at the head, by the routing table of references/check.md.

usage: pick-check-strategy.py [--ref <base>] [--refactor] [<file>...]

Lists the files the head changes against the merge base with <base> (default `main`), committed or not, with each <file> the task
will change, named before building when nothing has changed yet, and picks the table's first row one of whose patterns matches one of
them, `--refactor` matching when given and `none` when no file is changed or named. Prints the playbook's path, the `Strategy:` line
naming it from the references folder, for the change's body and the `judge` brief, and the judge's tier the playbook names, the one it
names for a small change when the change adds and removes fewer lines than the playbook says and no <file> is named, then exits 0;
exits 1 naming the cause when git cannot read the change or the table names no row that fits.
Standard library only, Python 3.9."""

import fnmatch
import math
import pathlib
import re
import subprocess
import sys

REFERENCES = pathlib.Path(__file__).resolve().parents[1] / "references"
ROW = re.compile(r"^\| [^|]+ \| (?P<patterns>[^|]+) \| \[[^]]+\]\((?P<playbook>[^)]+)\) \|$")
TIER = re.compile(r"\*\*Judge tier\*\*: (?P<tier>[^;\n]+?)(?:; under (?P<lines>\d+) changed lines, (?P<small>[^\n]+?))?\.?$", re.M)


def changed(base):
    """(the files, the count of lines added and removed) of the head against the merge base with BASE, committed or not, a moved file under both its names; a binary file counts as too many lines to be small."""
    merge_base = subprocess.run(["git", "merge-base", base, "HEAD"], capture_output=True, text=True)
    if merge_base.returncode:
        sys.exit(f"pick-check-strategy: git found no merge base of {base} and the head: {merge_base.stderr.strip()}")
    listed = subprocess.run(["git", "-c", "core.quotepath=false", "diff", "--numstat", "--no-renames", merge_base.stdout.strip()], capture_output=True, text=True)
    untracked = subprocess.run(["git", "-c", "core.quotepath=false", "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True)
    files, lines = [], 0
    for added, removed, file in (line.split("\t", 2) for line in listed.stdout.splitlines()):
        files.append(file)
        lines += math.inf if added == "-" else int(added) + int(removed)
    for file in untracked.stdout.splitlines():
        files.append(file)
        lines += len(pathlib.Path(file).read_bytes().splitlines())
    return files, lines


def pick(files, refactor):
    for line in (REFERENCES / "check.md").read_text().splitlines():
        match = ROW.match(line)
        if not match:
            continue
        patterns = re.findall(r"`([^`]+)`", match["patterns"])
        fits = (refactor if patterns == ["--refactor"] else not files if match["patterns"].strip() == "none"
                else any(fnmatch.fnmatch(file, pattern) for file in files for pattern in patterns))
        if fits:
            return match["playbook"]
    sys.exit("pick-check-strategy: no row of references/check.md fits this change, so the table lacks a case")


def main(args):
    refactor = "--refactor" in args
    words = [arg for arg in args if arg != "--refactor"]
    base = "main"
    if words[:1] == ["--ref"]:
        base = "".join(words[1:2]) or "-"
        words = words[2:]
    if any(word.startswith("-") for word in [base, *words]):
        print(__doc__, file=sys.stderr)
        return 2
    files, lines = changed(base)
    playbook = pick(files + words, refactor)
    path = REFERENCES / playbook
    tier = TIER.search(path.read_text())  # every playbook names its judge's tier, as the strategy replay checks
    small = tier["small"] and not words and lines < int(tier["lines"])
    print(f"playbook: {path}\nStrategy: {playbook}.\n"
          f"Open only this playbook; put the `Strategy:` line in the change's body and in the `judge` brief, and start the judge at {tier['small'] if small else tier['tier']}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

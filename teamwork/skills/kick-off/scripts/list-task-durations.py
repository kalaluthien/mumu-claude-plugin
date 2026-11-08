#!/usr/bin/env python3
"""Print one row per closed issue that holds no parts: number, labels, criteria count, start, end, hours and where the start came
from (`pr`: first commit of the pull request that closed it; `created`: no such pull request, so its creation), then
the count of rows per start source.

usage: list-task-durations.py
       list-task-durations.py --from-json <file>

It reads the board of the repository the current folder is in; `--from-json` reads a fixture list of issues instead."""
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import task_history  # noqa: E402


def main(args):
    if len(args) == 2 and args[0] == "--from-json" and not args[1].startswith("--"):
        issues = json.load(open(args[1]))
    elif not args:
        issues = task_history.fetch(task_history.own_repository())
    else:
        print(__doc__, file=sys.stderr)
        return 2
    table = task_history.rows(issues)
    print("number\tlabels\tcriteria\tstart\tend\thours\tsource")
    for row in table:
        print(f"{row['number']}\t{','.join(row['labels'])}\t{row['criteria']}\t{row['start']}\t{row['end']}\t{row['hours']:.1f}\t{row['source']}")
    counts = collections.Counter(row["source"] for row in table)
    print(f"rows: {len(table)} (pr {counts['pr']}, created {counts['created']}); hours run from the start source to the close")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

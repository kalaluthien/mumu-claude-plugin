#!/usr/bin/env python3
"""usage: list-task-durations.py <owner/repo> | --from-json <file>

Print one row per closed non-backlog issue: number, labels, criteria count, start, end, hours and where the start came
from (`pr`: first commit of the pull request that closed it; `created`: no such pull request, so its creation), then
the count of rows per start source. `--from-json` reads a fixture list of issues instead of GitHub."""
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import task_history  # noqa: E402


def main(argv):
    if len(argv) == 2 and argv[0] == "--from-json":
        issues = json.load(open(argv[1]))
    elif len(argv) == 1 and "/" in argv[0]:
        issues = task_history.fetch(argv[0])
    else:
        sys.exit(__doc__)
    table = task_history.rows(issues)
    print("number\tlabels\tcriteria\tstart\tend\thours\tsource")
    for r in table:
        print(f"{r['number']}\t{','.join(r['labels'])}\t{r['criteria']}\t{r['start']}\t{r['end']}\t{r['hours']:.1f}\t{r['source']}")
    counts = collections.Counter(r["source"] for r in table)
    print(f"rows: {len(table)} (pr {counts['pr']}, created {counts['created']}); hours run from the start source to the close")


if __name__ == "__main__":
    main(sys.argv[1:])

#!/usr/bin/env python3
"""Print the checks a pull request's diff needs, one per line, the judge first with its model: what `pr-merge.py` requires a pass of.

usage: check-scope.py <pr-url>
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import gh  # noqa: E402
import scope  # noqa: E402

URL = re.compile(r"https://github\.com/([\w.-]+/[\w.-]+)/pull/\d+")

if __name__ == "__main__":
    if len(sys.argv) != 2 or not (m := URL.fullmatch(sys.argv[1])):
        sys.exit("usage: check-scope.py <pr-url>")
    try:
        pr = json.loads(gh.gh("pr", "view", sys.argv[1], "--json", "headRefOid,baseRefName"))
        mapping, ahead, tree = gh.change(m[1], pr["baseRefName"], pr["headRefOid"])
        need = scope.needs(scope.changed(ahead), mapping, scope.names(tree) if tree else set())
    except (RuntimeError, ValueError, KeyError, TypeError) as e:
        sys.exit(f"check-scope.py: could not read {sys.argv[1]}'s scope: {e}")
    lines = scope.lines(ahead)
    for check in need:
        print(f"judge: {scope.model(lines)} ({lines} changed lines)" if check == scope.JUDGE else check)

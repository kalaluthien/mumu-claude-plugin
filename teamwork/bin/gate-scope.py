#!/usr/bin/env python3
"""Print the gates a pull request's diff needs, one per line, the judge first with its model: what `pr-merge.py` requires a pass of.

usage: gate-scope.py <pr-url>
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
        sys.exit("usage: gate-scope.py <pr-url>")
    try:
        pr = json.loads(gh.gh("pr", "view", sys.argv[1], "--json", "headRefOid,baseRefName"))
        mapping, ahead, tree = gh.change(m[1], pr["baseRefName"], pr["headRefOid"])
        need = scope.needs(scope.changed(ahead), mapping, scope.names(tree) if tree else set())
    except (RuntimeError, ValueError, KeyError, TypeError) as e:
        sys.exit(f"gate-scope.py: could not read {sys.argv[1]}'s scope: {e}")
    for gate in need:
        print(f"judge: {scope.JUDGE_MODEL}" if gate == scope.JUDGE else gate)

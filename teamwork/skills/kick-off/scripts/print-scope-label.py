#!/usr/bin/env python3
"""Print the `scope:` label of a manager's backlogs: the setting `scope_prefix` and the project in the manager's name, the only label that fits.
A name that is no `<project>-manager` name, or whose project is not lowercase words joined by `-` and at most 22 characters, gets exit 2, so a wrong label is never printed.

usage: print-scope-label.py <manager-name>
       print-scope-label.py --me"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import session  # noqa: E402
import team_names  # noqa: E402
import team_settings  # noqa: E402


def main(args):
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    name = session.sessions()[1].get("name", "") if args == ["--me"] else args[0]
    if team_names.role(name) != "manager" or not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", team_names.project(name)) or len(team_names.project(name)) > 22:
        print(__doc__, file=sys.stderr)
        return 2
    print(team_settings.load(".")["scope_prefix"] + team_names.project(name))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

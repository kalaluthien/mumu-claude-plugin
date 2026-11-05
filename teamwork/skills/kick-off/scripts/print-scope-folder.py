#!/usr/bin/env python3
"""Print the folder a manager's root tasks are filed in, `--scope`'s value: the top-level folder named like the project in the manager's name, else an empty line for the repository root.
A name that is no `<project>-manager` name, or whose project is not lowercase words joined by `-` and at most 22 characters, gets exit 2, so a wrong folder is never printed.

usage: print-scope-folder.py <manager-name>
       print-scope-folder.py --me"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board_scope  # noqa: E402
import session  # noqa: E402
import team_names  # noqa: E402


def main(args):
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    name = session.sessions()[1].get("name", "") if args == ["--me"] else args[0]
    project = team_names.project(name)
    if team_names.role(name) != "manager" or not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", project) or len(project) > 22:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        print(board_scope.folder_of(project))
    except LookupError as e:
        print(f"print-scope-folder: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

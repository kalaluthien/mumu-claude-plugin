#!/usr/bin/env python3
"""Print per name and project folder its sessions, restarts (a further session of the same name in that folder), the hours
each restart cost and, apart,
its idle gaps over 30 minutes inside a session (a wait for the owner, not a restart).

usage: list-session-gaps.py [--from-folder <projects folder>] [--json] <name>...

A name with no transcript
prints "no session record". The default folder is the Claude config folder's projects; `--json` prints the rows for the estimator."""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import claude_config  # noqa: E402
import session_gaps  # noqa: E402
import usage_parser  # noqa: E402


def main(args):
    parser = usage_parser.parser(__doc__, description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from-folder", type=pathlib.Path, default=claude_config.folder() / "projects")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("names", nargs="+")
    options = parser.parse_args(args)
    rows = session_gaps.summaries(options.from_folder, options.names)
    if options.json:
        print(json.dumps(rows))
        return
    print("worker\tproject\tsessions\trestarts\trestart hours\tidle gaps")
    for name in options.names:
        for row in [row for row in rows if row["worker"] == name] or [None]:
            if row is None:
                print(f"{name}\tno session record")
            else:
                hours = ",".join(f"{hour:.1f}" for hour in row["restart_hours"]) or "-"
                print(f"{name}\t{row['project']}\t{row['sessions']}\t{row['restarts']}\t{hours}\t{row['idle_gaps']}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

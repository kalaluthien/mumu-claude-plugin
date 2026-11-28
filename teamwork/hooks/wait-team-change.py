#!/usr/bin/env python3
"""Print `changed` once at start, then once per burst of marks by team sessions to the tasks of the current folder's repository, after the mark has been quiet for QUIET seconds, until killed.

usage: wait-team-change.py
It looks at the signal file's change time every POLL seconds, so it reads no board and runs on any OS."""
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import team_signal  # noqa: E402

POLL = 1  # seconds between looks at the signal file
QUIET = 2  # seconds without a mark that end a burst


def main(args):
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    seen = team_signal.stamp()
    print("changed", flush=True)
    while True:
        time.sleep(POLL)
        if team_signal.stamp() == seen:
            continue
        # one `changed` per burst: a session often marks several writes in a row, and each would otherwise read the board
        while team_signal.stamp() != seen:
            seen = team_signal.stamp()
            time.sleep(QUIET)
        print("changed", flush=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Print whether Remote Control is active in this session, and so whether a push (`notify`) reaches the owner away.

usage: print-remote-control.py"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import remote_control  # noqa: E402


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    if remote_control.active(os.environ.get("CLAUDE_CODE_SESSION_ID")):
        print("active: Remote Control is on in this session; send a `notify` push where a step says to.")
    else:
        print("inactive: Remote Control is off in this session; send no push, and keep the step in your tab.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

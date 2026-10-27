#!/usr/bin/env python3
"""Prints one line per named live agent: name, pane id, workspace id, status; an unnamed session has no name key, so it is skipped.
`--me` prints only this session's name, or nothing outside a named session.

usage: list-sessions.py
       list-sessions.py --me"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import session  # noqa: E402


def main(args):
    if args not in ([], ["--me"]):
        print(__doc__, file=sys.stderr)
        return 2
    listed, me = session.sessions()
    if args == ["--me"]:
        return print(me.get("name", "")) if me.get("name") else None
    for a in listed:
        if a.get("name"):
            print(a["name"], a.get("pane_id", "-"), a.get("workspace_id", "-"), a.get("agent_status", "-"))
    if not listed:
        print(f"list-sessions.py: {session.EMPTY}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

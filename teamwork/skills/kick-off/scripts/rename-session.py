#!/usr/bin/env python3
"""Rename this session to <name> in herdr (tab, pane, agent) and in Claude Code (a `/rename` prompt), then read the name Claude Code
recorded from the session's transcript and send the prompt again until it is exactly <name>; print `renamed to <name>`, or
`not renamed to <name>: <reason>` and exit 1. A typed prompt can land garbled, such as `teamwork-manager teamwork-`, so one send is not proof.

usage: rename-session.py <name>"""
import json
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import session  # noqa: E402

TRIES = 3
SETTLE = 8  # seconds Claude Code takes to record a name, measured at 1-6


def recorded(session_id):
    """The last name Claude Code wrote for this session, or None."""
    name = None
    for path in (pathlib.Path.home() / ".claude" / "projects").glob(f"*/{session_id}.jsonl"):
        for line in path.read_text(errors="replace").splitlines():
            if line.startswith('{"type":"custom-title"'):
                name = json.loads(line).get("customTitle")
    return name


def main(args):
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    name = args[0]
    _, me = session.sessions()
    if not me:
        print(f"not renamed to {name}: no herdr session owns this pane")
        return 1
    session.rename(me, name)
    session.herdr("agent", "rename", me["pane_id"], name)
    session_id = (me.get("agent_session") or {}).get("value")
    for _ in range(TRIES):
        if session.prompt(me["pane_id"], f"/rename {name}"):
            continue
        deadline = time.time() + SETTLE
        while time.time() < deadline and recorded(session_id) != name:
            time.sleep(1)
        if recorded(session_id) == name:
            print(f"renamed to {name}")
            return 0
    print(f"not renamed to {name}: Claude Code recorded {recorded(session_id)!r}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

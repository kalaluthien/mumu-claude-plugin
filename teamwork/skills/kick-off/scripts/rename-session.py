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
    """Every name Claude Code wrote for this session, oldest first."""
    names = []
    for path in (pathlib.Path.home() / ".claude" / "projects").glob(f"*/{session_id}.jsonl"):
        for line in path.read_text(errors="replace").splitlines():
            if line.startswith('{"type":"custom-title"'):
                names.append(json.loads(line).get("customTitle"))
    return names


def main(args):
    if len(args) != 1 or args[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    name = args[0]
    _, me = session.sessions()
    if not me:
        print(f"not renamed to {name}: no herdr session owns this pane")
        return 1
    session_id = (me.get("agent_session") or {}).get("value")
    if not session_id:
        print(f"not renamed to {name}: herdr gives this session no id, so its transcript cannot be read")
        return 1
    session.rename(me, name)
    session.herdr("agent", "rename", me.get("name") or me["pane_id"], name)  # its name, resolved on each call, since herdr may move the pane
    refused = None
    for _ in range(TRIES):
        before = len(recorded(session_id))
        refused = session.prompt(name, f"/rename {name}")  # herdr's new name, resolved on each call, since it may move the pane
        if refused:
            time.sleep(SETTLE)
            continue
        deadline = time.time() + SETTLE
        while time.time() < deadline:
            names = recorded(session_id)
            if len(names) > before and names[-1] == name:  # a new record, not an old one that happens to match
                print(f"renamed to {name}")
                return 0
            time.sleep(1)
    reason = f"herdr refused the prompt: {refused}" if refused else f"Claude Code recorded {recorded(session_id)[-1:]}"
    print(f"not renamed to {name}: {reason}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

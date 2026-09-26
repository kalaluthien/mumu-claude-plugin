#!/usr/bin/env python3
"""Stop hook: refuse a lead's stop while it holds work and its `team-watch` is not running.

Only `agent_type` `mumu-team:lead` is read; any other session, a worker's
included, stops and reads nothing, since a stalled worker is its lead's `idle`
line. What `gh` cannot read lets the lead stop, so an outage never traps it.

Lead: refused only while its checkout's repository has an open root goal or
root task and no `team-watch` process descends from `$CLAUDE_PID`; the reason
names the command to arm with the Monitor tool.
"""
import json
import os
import pathlib
import sys

SCRIPTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parent / "lib"))
import gh  # noqa: E402
from command import run  # noqa: E402

payload = json.load(sys.stdin)
cwd = payload.get("cwd") or "."


def block(reason):
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def watching(root):
    """Whether a `team-watch.py` process descends from pid `root`."""
    table = run("ps", "-axo", "pid=,ppid=,command=").splitlines()
    rows = [(int(r[0]), int(r[1]), r[2] if len(r) > 2 else "") for r in (line.split(None, 2) for line in table)]
    parent = {pid: ppid for pid, ppid, _ in rows}

    def descends(pid):
        seen = set()
        while pid in parent and pid not in seen:
            seen.add(pid)
            pid = parent[pid]
            if pid == root:
                return True
        return False

    return any("/team-watch.py" in command and descends(pid) for pid, _, command in rows)


def lead():
    held = gh.held(cwd)
    if held and not watching(int(os.environ.get("CLAUDE_PID") or os.getppid())):
        block(f"You hold open root goals or root tasks ({' '.join(held)}) and `team-watch` is not running: arm "
              f"`\"{SCRIPTS / 'team-watch.py'}\"` with the Monitor tool at its longest timeout, in your checkout, before you stop.")


if payload.get("agent_type") == "mumu-team:lead":
    lead()

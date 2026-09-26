#!/usr/bin/env python3
"""Stop hook: refuse a lead's stop while its repository has an open root goal or root task and no `team-watch` descends from `$CLAUDE_PID`.

Any other session stops unread; what `gh` cannot read lets the lead stop.
"""
import json
import os
import pathlib
import sys

SCRIPTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parent / "lib"))
import gh  # noqa: E402
from command import run  # noqa: E402


def watching(root):
    """Whether a `team-watch.py` process descends from pid `root`."""
    rows = [line.split(None, 2) for line in run("ps", "-axo", "pid=,ppid=,command=").splitlines()]
    parent = {int(r[0]): int(r[1]) for r in rows}
    for pid in (int(r[0]) for r in rows if len(r) > 2 and "/team-watch.py" in r[2]):
        seen = set()
        while pid in parent and pid not in seen and pid != root:
            seen.add(pid)
            pid = parent[pid]
        if pid == root:
            return True
    return False


payload = json.load(sys.stdin)
held = payload.get("agent_type") == "mumu-team:lead" and gh.held(payload.get("cwd") or ".")
if held and not watching(int(os.environ.get("CLAUDE_PID") or os.getppid())):
    print(json.dumps({"decision": "block", "reason": f"You hold open root goals or root tasks ({' '.join(held)}) and `team-watch` is not running: arm "
                      f"`\"{SCRIPTS / 'team-watch.py'}\"` with the Monitor tool at its longest timeout, in your checkout, before you stop."}))

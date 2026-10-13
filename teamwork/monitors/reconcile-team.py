#!/usr/bin/env python3
"""The `reconcile-team` monitor: tell a manager, once per change, each gap between GitHub and its team and the action
that closes it, so the manager works from observed state rather than remembered events. Silent in a session whose
name does not end in `-manager`, since a worker starts the same skill."""
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import team  # noqa: E402

POLL = float(os.environ.get("MONITOR_POLL", 60))  # GitHub reads each poll; a minute keeps them far under the rate limit

shown = set()
while True:
    listed, me = team.sessions()
    lines = team.manager_actions(me, listed) if me.get("name", "").endswith("-manager") else []
    for line in lines:
        if line not in shown:
            print(line, flush=True)
    shown = set(lines)
    time.sleep(POLL)

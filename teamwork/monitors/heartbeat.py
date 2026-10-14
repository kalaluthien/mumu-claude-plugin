#!/usr/bin/env python3
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import team  # noqa: E402

POLL = float(os.environ.get("MONITOR_POLL", 60))  # GitHub reads each poll; a minute keeps them far under the rate limit

shown, staffed = set(), False  # the exit waits until this manager has had a worker, so a fresh manager routes first
while True:
    listed, me = team.sessions()
    manager = me.get("name", "").endswith("-manager")
    worker = me.get("name", "").endswith("-worker")
    lines = team.manager_actions(me, listed) if manager else team.worker_actions(me) if worker else []
    if manager and lines is not None:
        crew = team.members(me, listed)
        staffed = staffed or bool(crew)
        if staffed and not crew and not lines:  # an open issue to route or answer is work not yet done
            lines.append(team.exit_action(me, listed))
    for line in lines or []:  # a failed read (None) keeps what was shown, so the next poll repeats nothing
        if line not in shown:
            print(line, flush=True)
    shown = shown if lines is None else set(lines)
    time.sleep(POLL)

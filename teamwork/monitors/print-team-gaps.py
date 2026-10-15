#!/usr/bin/env python3
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import herdr_agents  # noqa: E402
import team_gaps  # noqa: E402

POLL = float(os.environ.get("MONITOR_POLL", 60))  # GitHub reads each poll; a minute keeps them far under the rate limit

shown, staffed = set(), False  # the exit waits until this manager has had a worker, so a fresh manager routes first
waiting = set()  # a worker's issues with an open blocker, so a restart reports no blocker closed long ago
while True:
    listed, me = herdr_agents.sessions()
    manager = me.get("name", "").endswith("-manager")
    worker = me.get("name", "").endswith("-worker")
    lines = team_gaps.manager_actions(me, listed) if manager else team_gaps.worker_actions(me, waiting) if worker else []
    if manager and lines is not None:
        crew = herdr_agents.members(me, listed)
        staffed = staffed or bool(crew)
        idle = not crew and not lines  # an open issue to route or answer is work not yet done
        staffed = staffed or idle and team_gaps.had_worker(me)  # a restart lost the memory of a worker, so GitHub gives it back
        if staffed and idle:
            lines.append(team_gaps.exit_action(me, listed))
    for line in lines or []:  # a failed read (None) keeps what was shown, so the next poll repeats nothing
        if line not in shown:
            print(line, flush=True)
    shown = shown if lines is None else set(lines)
    time.sleep(POLL)

#!/usr/bin/env python3
import os
import pathlib
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import herdr_agents  # noqa: E402
import team_gaps  # noqa: E402
import team_signal  # noqa: E402

POLL = float(os.environ.get("MONITOR_POLL", 60))  # herdr is read each poll, which costs no GitHub points
REFRESH = float(os.environ.get("MONITOR_REFRESH", 900))  # a change made outside the team, such as the owner's comment on the web, sends no signal
SKEW = timedelta(seconds=5)  # GitHub's clock against ours


def read(manager, me, staffed, since):
    return team_gaps.manager_read(me, history=not staffed, since=since) if manager else team_gaps.worker_read(me)


shown, staffed = set(), False  # the exit waits until this manager has had a worker, so a fresh manager routes first
waiting = set()  # a worker's issues with an open blocker, so a restart reports no blocker closed long ago
fed = set()  # the reports a manager was already fed
data, read_at, signal = None, 0.0, team_signal.stamp()  # what GitHub last gave, when, and the signal file's change then
while True:
    listed, me = herdr_agents.sessions()
    role = herdr_agents.role(me.get("name"))
    manager, worker = role == "manager", role == "worker"
    # GitHub is read when a team session signals a change or REFRESH has passed, and in full only when it first asks cheaply and something changed
    if (manager or worker) and (data is None or team_signal.stamp() != signal or time.time() - read_at >= REFRESH):
        now, seen = datetime.now(timezone.utc), team_signal.stamp()  # both taken before the read, so a touch during it still differs
        since = (datetime.fromtimestamp(read_at, timezone.utc) - SKEW).strftime("%Y-%m-%dT%H:%M:%SZ")
        if data is None or team_gaps.changed_since(since):
            data = read(manager, me, staffed, since if read_at else None)
        if data is not None:  # a failed read keeps the last good time, so the next read still feeds what came after it
            read_at, signal = now.timestamp(), seen
    lines = [] if not (manager or worker) else None if data is None else team_gaps.manager_actions(me, listed, data, fed) if manager else team_gaps.worker_actions(me, waiting, data)
    if manager and lines is not None:
        crew = herdr_agents.members(me, listed)
        staffed = staffed or bool(crew)
        idle = not crew and not data["found"] and not data["outside"]  # any open issue, deferred ones included, is work not yet done
        staffed = staffed or idle and data["had_worker"]  # a restart lost the memory of a worker, so GitHub gives it back
        if staffed and idle:
            lines += filter(None, [team_gaps.exit_action(me, listed)])
    for line in lines or []:  # a failed read (None) keeps what was shown, so the next poll repeats nothing
        if line not in shown:
            print(line, flush=True)
    shown = shown if lines is None else set(lines)
    time.sleep(POLL)

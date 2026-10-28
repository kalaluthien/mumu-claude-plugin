#!/usr/bin/env python3
"""Print one line per action the team session's board and sessions call for, each once, polling until killed.

usage: print-team-gaps.py
It takes the session's role from herdr, reads the board when a team session signals a change or MONITOR_REFRESH seconds pass, and polls every MONITOR_POLL seconds."""
import os
import pathlib
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import board  # noqa: E402
import landing  # noqa: E402
import session  # noqa: E402
import team_gaps  # noqa: E402
import team_names  # noqa: E402
import team_signal  # noqa: E402

POLL = float(os.environ.get("MONITOR_POLL", 60))  # the sessions are read each poll, which costs no GitHub points
REFRESH = float(os.environ.get("MONITOR_REFRESH", 900))  # a change made outside the team, such as the owner's comment on the web, sends no signal
SKEW = timedelta(seconds=5)  # GitHub's clock against ours


def read(manager, me, had_worker, since):
    return team_gaps.manager_read(me, history=not had_worker, since=since) if manager else team_gaps.worker_read(me)


def main(args):
    shown, had_worker = set(), False  # the exit waits until this manager has had a worker, so a fresh manager routes first
    waiting = set()  # a worker's issues with an open blocker, so a restart reports no blocker closed long ago
    reported = set()  # the reports a manager was already reported
    data, read_at, signal = None, 0.0, team_signal.stamp()  # what GitHub last gave, when, and the signal file's change then
    ports = None  # the board and landing the last read used
    while True:
        if ports != (board.kind(), landing.kind()):
            # a setting written after the start names another board, which the last read never saw; the signal wakes the issue pane to read it too
            if ports is not None:
                data, read_at = None, 0.0
                team_signal.SIGNAL.parent.mkdir(parents=True, exist_ok=True)
                team_signal.SIGNAL.touch()
            ports = (board.kind(), landing.kind())
        listed, me = session.sessions()
        role = team_names.role(me.get("name"))
        manager, worker = role == "manager", role == "worker"
        # GitHub is read when a team session signals a change or REFRESH has passed, and in full only when it first asks cheaply and something changed
        if (manager or worker) and (data is None or team_signal.stamp() != signal or time.time() - read_at >= REFRESH):
            now, seen = datetime.now(timezone.utc), team_signal.stamp()  # both taken before the read, so a touch during it still differs
            since = (datetime.fromtimestamp(read_at, timezone.utc) - SKEW).strftime("%Y-%m-%dT%H:%M:%SZ")
            checks = {board.changed_since, landing.changed_since}  # one function when both ports read GitHub, so its read runs once
            if data is None or any(check(since) for check in checks):
                data = read(manager, me, had_worker, since if read_at else None)
            if data is not None:  # a failed read keeps the last good time, so the next read still feeds what came after it
                read_at, signal = now.timestamp(), seen
        lines = [] if not (manager or worker) else None if data is None else team_gaps.manager_actions(me, listed, data, reported) if manager else team_gaps.worker_actions(me, waiting, data)
        if manager and lines is not None:
            workers = team_names.workers(me, listed)
            had_worker = had_worker or bool(workers)
            idle = not workers and not data["found"] and not data["outside"]  # any open issue, deferred ones included, is work not yet done
            had_worker = had_worker or idle and data["had_worker"]  # a restart lost the memory of a worker, so GitHub gives it back
            if had_worker and idle:
                lines += filter(None, [team_gaps.exit_action(me, listed)])
        for line in lines or []:  # a failed read (None) keeps what was shown, so the next poll repeats nothing
            if line not in shown:
                print(line, flush=True)
        shown = shown if lines is None else set(lines)
        time.sleep(POLL)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

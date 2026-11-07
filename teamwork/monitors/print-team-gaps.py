#!/usr/bin/env python3
"""Print one line per action the team session's board and sessions call for, each once, polling until killed.

usage: print-team-gaps.py
It takes the session's role from herdr and watches only while a worker lives for a manager, always for a worker, never for another session; it reads the board when a team session signals a change or MONITOR_REFRESH seconds pass, and polls every MONITOR_POLL seconds."""
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import board  # noqa: E402
import iso_time  # noqa: E402
import landing  # noqa: E402
import session  # noqa: E402
import team_gaps  # noqa: E402
import team_names  # noqa: E402
import team_signal  # noqa: E402

POLL = float(os.environ.get("MONITOR_POLL", 60))  # the sessions are read each poll, which costs no board read
REFRESH = float(os.environ.get("MONITOR_REFRESH", 900))  # a change made outside the team, such as the owner's comment on the web, sends no signal
SKEW = 5  # seconds the board's clock may differ from ours


def read(manager, me, since):
    return team_gaps.manager_read(me, since=since) if manager else team_gaps.worker_read(me)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    shown = set()
    waiting = set()  # a worker's issues with an open blocker, so a restart reports no blocker closed long ago
    fed_urls = set()  # the urls of the reports a manager was already fed
    data, read_at, signal = None, 0.0, team_signal.stamp()  # what the board last gave, when, and the signal file's change then
    awake = False  # whether the last poll watched, so the poll the team empties in still reads once
    while True:
        listed, me = session.sessions()
        watching = team_names.watching(me, listed)
        manager = team_names.role(me.get("name")) == "manager"
        if not watching and not (awake and manager):
            # a plugin monitor that exits is never started again, so a team with no worker is waited out here; the next worker's first read shows every open gap
            shown, waiting, fed_urls, data, read_at, awake = set(), set(), set(), None, 0.0, False
            time.sleep(POLL)
            continue
        # the last worker may have posted a report just before it left, which only this one more read feeds
        awake = watching
        # the board is read when a team session signals a change or REFRESH has passed, and in full only when it first asks cheaply and something changed
        if data is None or team_signal.stamp() != signal or time.time() - read_at >= REFRESH:
            now, seen = time.time(), team_signal.stamp()  # both taken before the read, so a touch during it still differs
            since = iso_time.stamp(read_at - SKEW)
            checks = {board.changed_since, landing.changed_since}
            if data is None or any(check(since) for check in checks):
                data = read(manager, me, since if read_at else None)
            if data is not None:  # a failed read keeps the last good time, so the next read still feeds what came after it
                read_at, signal = now, seen
        if data is None:
            lines = None
        elif manager:
            lines = team_gaps.manager_actions(me, listed, data, fed_urls)
        else:
            lines = team_gaps.worker_actions(me, waiting, data)
        for line in lines or []:  # a failed read (None) keeps what was shown, so the next poll repeats nothing
            if line not in shown:
                print(line, flush=True)
        shown = shown if lines is None else set(lines)
        time.sleep(POLL)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

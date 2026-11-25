#!/usr/bin/env python3
"""Print one line per action the team session's board and sessions call for, each once, polling until killed.

usage: print-team-gaps.py
It takes the session's role from herdr and watches only while a worker lives for a manager, always for a worker, never for another session; it reads the board when a team session signals a change or TEAMWORK_MONITOR_REFRESH seconds pass, and polls every TEAMWORK_MONITOR_POLL seconds.
When a file of its own code changes, such as by a merge pulled into the checkout, it runs the new code in its own process, once that code loads, so its output stays the session's monitor."""
import os
import pathlib
import subprocess
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

POLL = float(os.environ.get("TEAMWORK_MONITOR_POLL", 60))  # the sessions are read each poll, which costs no board read
REFRESH = float(os.environ.get("TEAMWORK_MONITOR_REFRESH", 900))  # a change made outside the team, such as the owner's comment on the web, sends no signal
SKEW = 5  # seconds the board's clock may differ from ours
SCRIPT = pathlib.Path(__file__).resolve()


def code_stamp():
    """The change time of this script and of each module of the plugin's lib, which a module imported late may come from; None while a pull removes one."""
    try:
        return {path: path.stat().st_mtime_ns for path in [SCRIPT, *sorted((SCRIPT.parents[1] / "lib").glob("*.py"))]}
    except OSError:
        return None


def run_new_code(stamp):
    """Replace this process by its changed code, keeping the pid and the output the session reads, since a plugin monitor that ends, even to load new code, is never started again; code that fails to load, such as one caught mid-pull or a script moved away, is left until a later poll."""
    loads = [sys.executable, "-c", "import runpy, sys; runpy.run_path(sys.argv[1], run_name='load')", str(SCRIPT)]  # runs every import but not main, exiting 0 only when all load, and 1 for a script moved away
    if code_stamp() != stamp and subprocess.run(loads, capture_output=True).returncode == 0:
        os.execv(sys.executable, [sys.executable, str(SCRIPT)])


def read(manager, me, since):
    return team_gaps.manager_read(me, since=since) if manager else team_gaps.worker_read(me)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    shown = set()
    waiting = set()  # a worker's tasks waiting on a task, so a restart reports no wait that ended long ago
    read_of = {}  # what a worker last read of each task it holds, so only a change prints
    fed_urls = set()  # the urls of the reports a manager was already fed
    data, read_at, signal = None, 0.0, team_signal.stamp()  # what the board last gave, when, and the signal file's change then
    awake = False  # whether the last poll watched, so the poll the team empties in still reads once
    stamp = code_stamp()
    while True:
        run_new_code(stamp)
        listed, me = session.own()
        watching = team_names.watching(me, listed)
        manager = team_names.role(me.get("name")) == "manager"
        if not watching and not (awake and manager):
            # a plugin monitor that exits is never started again, so a team with no worker is waited out here; the next worker's first read shows every open gap
            shown, waiting, read_of, fed_urls, data, read_at, awake = set(), set(), {}, set(), None, 0.0, False
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
            lines = team_gaps.worker_actions(me, waiting, read_of, data)
        for line in lines or []:  # a failed read (None) keeps what was shown, so the next poll repeats nothing
            if line not in shown:
                print(line, flush=True)
        shown = shown if lines is None else set(lines)
        time.sleep(POLL)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""The `team-watch` monitor, run in a lead's checkout: one line per change of its workers, and one while its team sits idle.

Lines: `<word> <name>` for `blocked`, `idle`, `working`, or `gone`; and `team idle
<minutes>m` once no worker has worked for `TEAM_WATCH_IDLE` seconds while a root
goal or root task is open, at most hourly. A failed poll is skipped; in a worker's
tab it exits. `MONITOR_POLL` is the interval, `MONITOR_TICKS` a test's poll count.
"""
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import gh  # noqa: E402
import herdr  # noqa: E402
import names  # noqa: E402

REPEAT = 3600
WORD = {"blocked": "blocked", "idle": "idle", "done": "idle", "working": "working"}


def changes(last, now):
    """Next `{name: word}` and the lines to print, from the last words and herdr's `{name: agent_status}` now."""
    words = {name: WORD.get(status, last.get(name, "working")) for name, status in now.items()}
    lines = [f"{w} {name}" for name, w in words.items() if w != last.get(name, "working")]
    return words, lines + [f"gone {name}" for name in last if name not in now]


def idle(state, working, now, after):
    """Next state `(quiet since, printed at)` and whether an idle line is due, from whether any worker works."""
    since, printed = state
    if working:
        return (None, None), False
    since = now if since is None else since
    due = now - since >= after and (printed is None or now - printed >= REPEAT)
    return (since, printed), due


def main():
    if os.environ.get("MUMU_ROLE") == "worker":
        return
    checkout = os.getcwd()
    interval = float(os.environ.get("MONITOR_POLL", 10))
    ticks = int(os.environ.get("MONITOR_TICKS", 0))
    after = float(os.environ.get("TEAM_WATCH_IDLE", 1200))
    last, state, n = {}, (None, None), 0
    while not ticks or n < ticks:
        n += 1
        try:
            listed = herdr.listed("agent")
        except RuntimeError:
            listed = None
        if listed is not None:
            last, lines = changes(last, names.workers(listed, checkout))
            now = time.time()
            state, due = idle(state, "working" in last.values(), now, after)
            if due and gh.held(checkout):
                state = (state[0], now)
                lines.append(f"team idle {int((now - state[0]) // 60)}m")
            for line in lines:
                print(line, flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()

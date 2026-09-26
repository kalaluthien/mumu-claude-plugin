#!/usr/bin/env python3
"""The `team-watch` monitor: one line per change of a lead's workers, and one while its team sits idle.

usage: team-watch.py, run in the lead's checkout by the plugin's `monitors.json`.

Lines: `<word> <name>` when a worker's herdr state changes, `<word>` being
`blocked`, `idle`, `working`, or `gone` once herdr no longer lists it; and
`team idle <minutes>m` once no worker has been `working` for `TEAM_WATCH_IDLE`
seconds (1200) while the checkout's repository has an open root goal or root
task, again at most once an hour while that holds. A worker is named
`<topic>-<n>-<k>`, so its task is issue `<n>`. It never exits for lack of goals, and a poll whose `herdr`
or `gh` call fails is skipped; in a worker's session (`MUMU_ROLE=worker`) it
exits at once. `MONITOR_POLL` is the poll interval in seconds (10), and
`MONITOR_TICKS` stops it after that many polls, for a test (unset: never).
"""
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import team  # noqa: E402

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
        listed = team.agents()
        if listed is not None:
            last, lines = changes(last, team.workers(listed, checkout))
            now = time.time()
            state, due = idle(state, "working" in last.values(), now, after)
            if due and team.held(checkout):
                state = (state[0], now)
                lines.append(f"team idle {int((now - state[0]) // 60)}m")
            for line in lines:
                print(line, flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()

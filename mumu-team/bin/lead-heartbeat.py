#!/usr/bin/env python3
"""Print `lead-heartbeat: team idle <minutes>m, mission <parent-url>...`, one url per parent, while no worker of this session's lead mission works.

Usage: lead-heartbeat.py <plugin data dir>, run by the `lead-heartbeat` monitor. The line
comes once no worker has been `working` for `LEAD_HEARTBEAT_AFTER` seconds (1200),
zero workers included, and again at most once an hour while that holds; any
worker working prints nothing and restarts the count. It catches the deadlock
no `worker-watch` change line can. The mission and the loop are `lib/team.py`'s.
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import team  # noqa: E402


def step(state, working, now, after):
    """Next state `(quiet since, printed at)` and whether to print, from whether any worker works."""
    since, printed = state
    if working:
        return (None, None), False
    since = now if since is None else since
    due = now - since >= after and (printed is None or now - printed >= team.REPEAT)
    return (since, now if due else printed), due


def main():
    after = float(os.environ.get("LEAD_HEARTBEAT_AFTER", 1200))
    state = (None, None)

    def tick(parents, workers, words, now):
        nonlocal state
        state, due = step(state, "working" in words.values(), now, after)
        return [f"lead-heartbeat: team idle {int((now - state[0]) // 60)}m, mission {' '.join(parents)}"] if due else []

    team.poll(sys.argv[1], tick)


if __name__ == "__main__":
    main()

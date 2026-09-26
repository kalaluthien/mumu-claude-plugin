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


def main():
    if os.environ.get("MUMU_ROLE") == "worker":
        return
    checkout, ticks = os.getcwd(), int(os.environ.get("MONITOR_TICKS", 0))
    interval, after = float(os.environ.get("MONITOR_POLL", 10)), float(os.environ.get("TEAM_WATCH_IDLE", 1200))
    last, since, printed, n = {}, None, None, 0  # the team quiet since, the idle line printed at
    while not ticks or n < ticks:
        n += 1
        try:
            last, lines = changes(last, names.workers(herdr.listed("agent"), checkout))
        except RuntimeError:
            time.sleep(interval)
            continue
        now = time.time()
        if "working" in last.values():
            since = printed = None
        else:
            since = since or now
            if now - since >= after and (printed is None or now - printed >= REPEAT) and gh.held(checkout):
                printed = now
                lines.append(f"team idle {int((now - since) // 60)}m")
        for line in lines:
            print(line, flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()

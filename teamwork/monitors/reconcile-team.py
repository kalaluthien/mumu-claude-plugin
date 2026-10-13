#!/usr/bin/env python3
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
import team  # noqa: E402

POLL = float(os.environ.get("MONITOR_POLL", 60))  # GitHub reads each poll; a minute keeps them far under the rate limit

shown = set()
while True:
    listed, me = team.sessions()
    lines = team.manager_actions(me, listed) if me.get("name", "").endswith("-manager") else []
    for line in lines or []:  # a failed read (None) keeps what was shown, so the next poll repeats nothing
        if line not in shown:
            print(line, flush=True)
    shown = shown if lines is None else set(lines)
    time.sleep(POLL)

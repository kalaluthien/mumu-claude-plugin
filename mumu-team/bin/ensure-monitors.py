#!/usr/bin/env python3
"""Print the command of each lead monitor this session does not run, one per line, for the Monitor tool; nothing when both run.

usage: ensure-monitors.py

The plugin starts `worker-watch` and `lead-heartbeat` only at session start,
and each ends once its mission is deleted (`lib/team.py`), so a lead that
writes a new mission later runs neither. A monitor counts as this session's
when its process descends from `$CLAUDE_PID`, the session's Claude process;
the data dir is that of this session's mission (`team.mission_file`), which
must exist first. A monitor whose process started before the last change to
its script or `lib/team.py` counts as not running, so a merge re-arms it. Line: `<monitor>: "<bin>/<monitor>.py" "<data dir>"`.
"""
import os
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import team  # noqa: E402

BIN = pathlib.Path(__file__).resolve().parent
MONITORS = ("worker-watch", "lead-heartbeat")


def changed(m):
    """The epoch of the last change to monitor `m`'s code."""
    return max(p.stat().st_mtime for p in (BIN / f"{m}.py", BIN.parent / "lib" / "team.py"))


def running(table, root):
    """The monitors among `table`'s `(pid, ppid, start, command)` rows whose process descends from pid `root` and started after its code last changed."""
    parent = {pid: ppid for pid, ppid, _, _ in table}

    def descends(pid):
        seen = set()
        while pid in parent and pid not in seen:
            seen.add(pid)
            pid = parent[pid]
            if pid == root:
                return True
        return False

    mine = [(m, start) for pid, _, start, command in table for m in MONITORS if f"/{m}.py" in command and descends(pid)]
    return {m for m, _ in mine} - {m for m, start in mine if start < changed(m)}


def ps():
    rows = []
    for line in subprocess.run(["ps", "-axo", "pid=,ppid=,lstart=,command="], capture_output=True, text=True, env=dict(os.environ, LC_ALL="C")).stdout.splitlines():
        pid, ppid, *start, command = (line.split(None, 7) + [""])[:8]
        rows.append((int(pid), int(ppid), time.mktime(time.strptime(" ".join(start), "%a %b %d %H:%M:%S %Y")), command))
    return rows


def main():
    mission = team.mission_file()
    if mission is None:
        print("ensure-monitors.py: no mission for this session; write its GOAL: line first", file=sys.stderr)
        return 1
    have = running(ps(), int(os.environ["CLAUDE_PID"]))
    for m in MONITORS:
        if m not in have:
            print(f'{m}: "{BIN / (m + ".py")}" "{mission.parent.parent}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())

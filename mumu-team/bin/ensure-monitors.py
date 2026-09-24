#!/usr/bin/env python3
"""Print the command of each lead monitor this session does not run, one per line, for the Monitor tool; nothing when both run.

usage: ensure-monitors.py

The plugin starts `worker-watch` and `lead-heartbeat` only at session start,
and each ends once its mission is deleted (`lib/team.py`), so a lead that
writes a new mission later runs neither. A monitor counts as this session's
when its process descends from `$CLAUDE_PID`, the session's Claude process;
the data dir is that of this session's mission (`team.mission_file`), which
must exist first. Line: `<monitor>: "<bin>/<monitor>.py" "<data dir>"`.
"""
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import team  # noqa: E402

BIN = pathlib.Path(__file__).resolve().parent
MONITORS = ("worker-watch", "lead-heartbeat")


def running(table, root):
    """The monitors among `table`'s `(pid, ppid, command)` rows whose process descends from pid `root`."""
    parent = {pid: ppid for pid, ppid, _ in table}

    def descends(pid):
        seen = set()
        while pid in parent and pid not in seen:
            seen.add(pid)
            pid = parent[pid]
            if pid == root:
                return True
        return False

    return {m for pid, _, command in table for m in MONITORS if f"/{m}.py" in command and descends(pid)}


def ps():
    rows = []
    for line in subprocess.run(["ps", "-axo", "pid=,ppid=,command="], capture_output=True, text=True).stdout.splitlines():
        pid, ppid, command = (line.split(None, 2) + [""])[:3]
        rows.append((int(pid), int(ppid), command))
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

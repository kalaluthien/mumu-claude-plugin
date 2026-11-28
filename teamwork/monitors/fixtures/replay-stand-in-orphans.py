#!/usr/bin/env python3
"""Check that a heartbeat fixture's busy stand-ins end when the runner that started them is killed outright, as a sweep's time limit kills it, and print `ok <case>` or
`fail <case>: <what it saw>`, then `PASS stand-in orphans` or `FAIL stand-in orphans`; exit 1 on any failure:
- `ended`: `replay-stuck-runs.py` and `replay-shell-pipeline-runs.py`, each running at its kill, which SIGKILL ends 3 s after its start, leave no process that spins carrying the runner's mark 15 s later.

usage: replay-stand-in-orphans.py"""
import os
import pathlib
import re
import signal
import subprocess
import sys
import time
import uuid

HERE = pathlib.Path(__file__).resolve().parent
RUNNERS = ("replay-stuck-runs.py", "replay-shell-pipeline-runs.py")
SPINNING = re.compile(r'-c import (?:os, )?time; t = time\.time\(\); exec\("while')  # a process that opens with the busy loop, not the sleeper that holds its text
START, WAIT = 3, 15


def spinning(mark):
    """The pids of the processes that carry MARK in their environment and run a busy loop."""
    listing = subprocess.run(["ps", "-E", "-ww", "-A", "-o", "pid=,command="], capture_output=True, text=True).stdout
    return [int(line.split()[0]) for line in listing.splitlines() if mark in line and SPINNING.search(line)]


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases("stand-in orphans")
    left = {}
    for runner in RUNNERS:
        mark = f"ORPHAN_MARK={uuid.uuid4().hex}"
        process = subprocess.Popen([sys.executable, HERE / runner], env={**os.environ, "ORPHAN_MARK": mark.split("=")[1]},
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(START)
        started = len(spinning(mark.split("=")[1]))
        os.kill(process.pid, signal.SIGKILL)
        killed = process.wait() == -signal.SIGKILL
        deadline = time.monotonic() + WAIT
        while spinning(mark.split("=")[1]) and time.monotonic() < deadline:
            time.sleep(0.5)
        left[runner] = (killed, started, spinning(mark.split("=")[1]))
        for pid in left[runner][1]:
            os.kill(pid, signal.SIGKILL)
    cases.step("ended", all(killed and started and not after for killed, started, after in left.values()), left)
    return cases.finish()


if __name__ == "__main__":
    sys.path.insert(0, str(HERE.parents[1] / "lib"))
    import replay_probe  # noqa: E402
    sys.exit(main(sys.argv[1:]))

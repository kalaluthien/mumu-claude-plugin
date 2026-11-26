#!/usr/bin/env python3
"""Run run-criteria.py `--base --timeout 2` on a temporary git repository whose check outlives its limit, and print `ok <case>` or `fail <case>: <what it saw>`
per case, then `PASS check timeout` or `FAIL check timeout`, and exit 1 on any failure:
- `setsid`: the check starts a child in a session of its own that holds the check's output open for a minute; the run reports the timeout within
  `LIMIT` seconds and the child is gone;
- `daemon`: the check starts a child that leaves the check's process tree before the limit and holds its output open; the run still reports the timeout
  within `LIMIT` seconds.

usage: replay-check-timeout.py"""
import os
import pathlib
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
LIMIT = 20  # the 2 s timeout with room for a loaded machine, and well short of the child's minute
CHILDREN = {"setsid": "os.setsid()", "daemon": "os.fork() and os._exit(0); os.setsid()"}


def body(case):
    holder = f"import os, time; {CHILDREN[case]}; time.sleep(60)  # check-timeout-{case}-{os.getpid()}"
    return ("## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints PASS; meets: the caller's need.\n\n"
            f"## Definition of done\n\n1. [check] **The probe prints PASS when it runs**: `python3 -c \"{holder}\" & sleep 60; echo FAIL` prints `PASS`; on base `FAIL`.\n")


def living(case):
    """The pids of CASE's child still running, since `ps -A` lists them by the marker their code carries."""
    marker = f"check-timeout-{case}-{os.getpid()}"
    return [int(line.split()[0]) for line in subprocess.run(["ps", "-A", "-o", "pid=,command="], capture_output=True, text=True).stdout.splitlines() if marker in line]


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases("check timeout")
    with replay_probe.scratch("check-timeout-") as work:
        box = replay_probe.Sandbox(work)
        for case in CHILDREN:
            started = time.monotonic()
            done = box.python(SCRIPT, "--base", "--ref", "main", "--timeout", "2", replay_probe.write_text(work, f"{case}.md", body(case)), timeout=120)
            took, left = time.monotonic() - started, living(case)
            for pid in left:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:  # it ended between `ps` and here
                    pass
            cases.step(case, took < LIMIT and "timed out after 2 s" in done.stdout and not (case == "setsid" and left),
                       f"took {took:.0f} s, {len(left)} children left, {done.stdout[-300:]} {done.stderr[-300:]}")
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

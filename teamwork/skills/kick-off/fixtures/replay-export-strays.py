#!/usr/bin/env python3
"""Run run-criteria.py `--base` on a temporary git repository whose check starts a process in a session of its own from a file of the export, and print `PASS` when the run read the check's row and that
process is gone once the check ends, else `FAIL: <what it saw>`, since an export of the base or a clone of a hunk's revert may leave a monitor polling for ever. Exit 1 on FAIL.

usage: replay-export-strays.py"""
import os
import pathlib
import signal
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
LINGERING = f"lingering-probe-{os.getpid()}.py"  # one name per run, since `ps -A` also lists the probe of a run beside this one
BODY = ("## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints PASS; meets: the caller's need.\n\n"
        "## Definition of done\n\n1. [check] **The probe prints PASS when it runs**: `python3 start.py; echo FAIL` prints `PASS`; on base `FAIL`.\n")


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("export-strays-") as work:
        box = replay_probe.Sandbox(work, commit=False)
        replay_probe.write_text(box.repository, LINGERING, "import time\ntime.sleep(120)\n")
        replay_probe.write_text(box.repository, "start.py", "import os, subprocess, sys\n"
                                f"subprocess.Popen([sys.executable, os.path.abspath('{LINGERING}')], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n")
        box.git("add", ".")
        box.git("commit", "-q", "-m", "base")
        done = box.python(SCRIPT, "--base", "--ref", "main", replay_probe.write_text(work, "body.md", BODY))
        strays = [line.split()[0] for line in subprocess.run(["ps", "-A", "-o", "pid=,command="], capture_output=True, text=True).stdout.splitlines() if LINGERING in line]
        for pid in strays:
            try:
                os.kill(int(pid), signal.SIGKILL)
            except ProcessLookupError:  # it ended between `ps` and here
                pass
    if "| base ok |" not in done.stdout or strays:
        return replay_probe.fail(f"the check's row was {'read' if '| base ok |' in done.stdout else 'not read'} and {len(strays)} of its processes outlived it: {done.stdout[-300:]}")
    return replay_probe.Cases().finish()

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Run run-criteria.py `--base` on a temporary git repository whose check starts a process in a session of its own from a file of the export, and print `PASS` when that
process is gone once the check ends, else `FAIL`, since an export of the head or of a hunk's revert may leave a monitor polling for ever. Exit 1 on FAIL.

usage: replay-export-strays.py"""
import os
import pathlib
import signal
import subprocess
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
LINGERING = "lingering-probe.py"
BODY = ("## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints PASS; meets: the caller's need.\n\n"
        "## Definition of done\n\n1. [check] **The probe prints PASS when it runs**: `python3 start.py; echo FAIL` prints `PASS`; on base `FAIL`.\n")


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="export-strays-"))
    os.environ.update(HOME=str(work), GIT_AUTHOR_NAME="probe", GIT_AUTHOR_EMAIL="probe@example.com", GIT_COMMITTER_NAME="probe", GIT_COMMITTER_EMAIL="probe@example.com")
    (work / LINGERING).write_text("import time\ntime.sleep(120)\n")
    (work / "start.py").write_text(f"import os, subprocess, sys\nsubprocess.Popen([sys.executable, os.path.abspath('{LINGERING}')], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n")
    for argv in (["init", "-q", "-b", "main"], ["add", "."], ["commit", "-q", "-m", "base"]):
        subprocess.run(["git", *argv], cwd=work, check=True, capture_output=True)
    body = work.parent / f"{work.name}-body.md"
    body.write_text(BODY)
    subprocess.run([sys.executable, str(SCRIPT), "--base", "--ref", "main", str(body)], cwd=work, capture_output=True, text=True)
    strays = [line.split()[0] for line in subprocess.run(["ps", "-A", "-o", "pid=,command="], capture_output=True, text=True).stdout.splitlines() if LINGERING in line]
    for pid in strays:
        os.kill(int(pid), signal.SIGKILL)
    print("FAIL" if strays else "PASS")
    return 1 if strays else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

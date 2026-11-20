#!/usr/bin/env python3
"""Run run-criteria.py `--base` on a temporary git repository whose base holds `old.py` and no `new.py`, on checks that quote `FAIL` on base. Print `ok <case>` or
`fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `new-python`: a check that runs a Python fixture the base lacks reads `base ok`;
- `new-shell`: the same for a shell script run by `bash`;
- `piped`: the same when the run is piped to `tail -1`;
- `present`: a fixture the base holds that prints another text is a `wrong base`;
- `mixed`: a missing fixture beside other output is a `wrong base`;
- `read`: a read of a missing file, which a text scan names no more than a run, is a `wrong base`;
- `quoted-error`: a missing script whose own error is quoted reads `base ok`;
- `outside`: a missing file outside the export, which no change adds, is a `wrong base`;
- `stray-ended`: a process a check starts in a session of its own, from a file of the export, is gone once the check ends, as an export of the head or of a hunk's revert may leave it running.

usage: replay-base-rows.py"""
import os
import pathlib
import signal
import subprocess
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
BODY = ("## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints PASS; meets: the caller's need.\n\n"
        "## Definition of done\n\n1. [check] **The probe prints PASS when it runs**: `{command}` prints `PASS`; on base `{quote}`.\n")
# each case: the check, the quote, the row it must get
CASES = {"new-python": ("python3 new.py", "FAIL", "base ok"),
         "new-shell": ("bash new.sh", "FAIL", "base ok"),
         "piped": ("python3 new.py | tail -1", "FAIL", "base ok"),
         "present": ("python3 old.py", "FAIL", "wrong base"),
         "mixed": ("python3 old.py; python3 new.py", "FAIL", "wrong base"),
         "read": ("grep foo new.py | tail -1", "FAIL", "wrong base"),
         "quoted-error": ("bash new.sh", "bash: new.sh: No such file or directory", "base ok"),
         "outside": ("python3 /nonexistent-folder/new.py", "FAIL", "wrong base"),
         "stray-ended": ("python3 start.py; echo FAIL", "FAIL", "base ok")}
LINGERING = "lingering-probe.py"


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="base-rows-"))
    os.environ.update(HOME=str(work), GIT_AUTHOR_NAME="probe", GIT_AUTHOR_EMAIL="probe@example.com", GIT_COMMITTER_NAME="probe", GIT_COMMITTER_EMAIL="probe@example.com")
    (work / "old.py").write_text("print('oops')\n")
    (work / LINGERING).write_text("import time\ntime.sleep(120)\n")
    (work / "start.py").write_text(f"import os, subprocess, sys\nsubprocess.Popen([sys.executable, os.path.abspath('{LINGERING}')], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n")
    for argv in (["init", "-q", "-b", "main"], ["add", "."], ["commit", "-q", "-m", "base"]):
        subprocess.run(["git", *argv], cwd=work, check=True, capture_output=True)
    wrong = []
    for case, (command, quote, row) in CASES.items():
        body = work.parent / f"{work.name}-{case}.md"
        body.write_text(BODY.format(command=command, quote=quote))
        done = subprocess.run([sys.executable, str(SCRIPT), "--base", "--ref", "main", str(body)], cwd=work, capture_output=True, text=True)
        print(f"ok {case}" if f"| {row} |" in done.stdout else f"fail {case}: {' '.join((done.stdout + done.stderr).split())[:400]}", flush=True)
        wrong += [case] * (f"| {row} |" not in done.stdout)
    strays = [line.split()[0] for line in subprocess.run(["ps", "-A", "-o", "pid=,command="], capture_output=True, text=True).stdout.splitlines() if LINGERING in line]
    for pid in strays:
        os.kill(int(pid), signal.SIGKILL)
    print(f"fail stray-ended: {len(strays)} process(es) of the export still run" if strays else "ok stray-ended-gone", flush=True)
    wrong += ["stray-ended"] * bool(strays)
    print("FAIL" if wrong else "PASS")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

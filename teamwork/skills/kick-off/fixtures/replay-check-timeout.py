#!/usr/bin/env python3
"""Run run-criteria.py `--base --timeout 2` on a temporary git repository whose check outlives its limit, and print `ok <case>` or `fail <case>: <what it saw>`
per case, then `PASS check timeout` or `FAIL check timeout`, and exit 1 on any failure:
- `setsid`: the check starts a child in a session of its own that holds the check's output open for a minute; the run reports the timeout within
  `LIMIT` seconds and the child is gone;
- `daemon`: the check starts a child that leaves the check's process tree before the limit and holds its output open; the run still reports the timeout
  within `LIMIT` seconds;
- `git`: `git archive` gives no answer, its stand-in first on `PATH` waiting on a child of its own; the run exits 1 within `LIMIT` seconds naming
  the call, and that child is gone;
- `fifo`: the check names a FIFO outside the repository, which no process writes, and prints a file the base holds; the run reads the FIFO never and
  prints the base row within `LIMIT` seconds;
- `left-group`: `git archive` starts a child that leaves its process group by `setsid` and holds the call's output open, then waits on it; the run
  exits 1 within `LIMIT` seconds naming the call, since it waits for the call alone, never for its output;
- `failed-archive`: `git archive` fails, its stand-in first on `PATH`; `--base` exits 1 naming the base it could not export, and `--hunks` naming HEAD;
- `ps`: `ps` gives no answer, its stand-in first on `PATH` waiting on a child of its own, and the check outlives its limit, so both the listing of
  its children and of the export's strays call `ps`; the run exits 1 within `LIMIT` seconds naming the call, and that child is gone;
- `held-stdin`: the run's stdin is a pipe held open and never written, and `git archive` reads its stdin to the end; the run gives each call no stdin,
  so it prints the base row within `LIMIT` seconds.

usage: replay-check-timeout.py"""
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
LIMIT = 20  # the 2 s timeout with room for a loaded machine, and well short of the child's minute
CHILDREN = {"setsid": "os.setsid()", "daemon": "os.fork() and os._exit(0); os.setsid()"}


def body(command):
    return ("## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints PASS; meets: the caller's need.\n\n"
            f"## Definition of done\n\n1. [check] **The probe prints PASS when it runs**: `{command}` prints `PASS`; on base `FAIL`.\n")


def holder(case):
    return f"python3 -c \"import os, time; {CHILDREN[case]}; time.sleep(60)  # check-timeout-{case}-{os.getpid()}\" & sleep 60; echo FAIL"


def ended(case):
    """Kills what is left of CASE's child, and says whether nothing was."""
    left = living(case)
    for pid in left:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:  # it ended between `ps` and here
            pass
    return not left


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
        def base(case, command, mode="--base", **variables):
            started = time.monotonic()
            done = box.python(SCRIPT, mode, "--ref", "main", "--timeout", "2", replay_probe.write_text(work, f"{case}.md", body(command)), timeout=60, **variables)
            return done, time.monotonic() - started

        def stand_in(case, archive):
            """A PATH whose `git` runs ARCHIVE for `git archive` and the real git for every other call."""
            folder = pathlib.Path(work, f"{case}-git")
            folder.mkdir()
            folder.joinpath("git").write_text(f'#!/bin/sh\n[ "$1" = archive ] && {archive}\nexec {shutil.which("git")} "$@"\n')
            folder.joinpath("git").chmod(0o755)
            return f"{folder}{os.pathsep}{box.environment['PATH']}"

        def hung(name):
            """A python3 that sleeps a minute in the background, marked as NAME's child, and is waited on, so the stand-in never answers."""
            return f'{{ python3 -c "import time; time.sleep(60)  # check-timeout-{name}-{os.getpid()}" & wait; }}'

        replay_probe.write_text(box.repository, "probe.txt", "FAIL\n")
        box.git("add", "probe.txt")
        box.git("commit", "-q", "-m", "Add the probe's output")

        for case in CHILDREN:
            done, took = base(case, holder(case))
            gone = ended(case)
            cases.step(case, took < LIMIT and "timed out after 2 s" in done.stdout and (case != "setsid" or gone),
                       f"took {took:.0f} s, children left: {not gone}, {done.stdout[-300:]} {done.stderr[-300:]}")
        done, took = base("git", "echo FAIL", PATH=stand_in("hung", hung("git")))
        gone = ended("git")
        cases.step("git", took < LIMIT and done.returncode == 1 and "`git archive` gave no answer in 2 s" in done.stderr and gone,
                   f"took {took:.0f} s, exit {done.returncode}, stand-in left: {not gone}, {done.stderr[-300:]}")
        left = f'{{ python3 -c "import os, time; os.setsid(); time.sleep(60)  # check-timeout-left-group-{os.getpid()}" & wait; }}'
        done, took = base("left-group", "echo FAIL", PATH=stand_in("left", left))
        for pid in living("left-group"):
            os.kill(pid, signal.SIGKILL)
        cases.step("left-group", took < LIMIT and done.returncode == 1 and "`git archive` gave no answer in 2 s" in done.stderr,
                   f"took {took:.0f} s, exit {done.returncode}, {done.stderr[-300:]}")
        fifo = pathlib.Path(work, "held.fifo")
        os.mkfifo(fifo)
        done, took = base("fifo", f"test -p {fifo} && cat probe.txt")
        cases.step("fifo", took < LIMIT and done.returncode == 0 and "| base ok | FAIL |" in done.stdout, f"took {took:.0f} s, exit {done.returncode}, {done.stdout[-300:]} {done.stderr[-300:]}")
        failing = stand_in("failed", "exit 128")
        refusals = [(mode, base(f"failed-{mode[2:]}", "echo FAIL", mode, PATH=failing)[0]) for mode in ("--base", "--hunks")]
        cases.step("failed-archive", [(done.returncode, done.stderr.strip()) for _, done in refusals]
                   == [(1, "run-criteria: could not export main; fetch it first"), (1, "run-criteria: could not export HEAD")], f"{[(done.returncode, done.stderr[-200:]) for _, done in refusals]}")
        folder = pathlib.Path(work, "hung-ps")
        folder.mkdir()
        replay_probe.write_text(folder, "ps", f"#!/bin/sh\n{hung('ps')}\n").chmod(0o755)
        done, took = base("ps", "sleep 30; echo FAIL", PATH=f"{folder}{os.pathsep}{box.environment['PATH']}")
        gone = ended("ps")
        cases.step("ps", took < LIMIT and done.returncode == 1 and "`ps -A` gave no answer in 2 s" in done.stderr and gone,
                   f"took {took:.0f} s, exit {done.returncode}, stand-in left: {not gone}, {done.stderr[-300:]}")
        started = time.monotonic()
        held = subprocess.Popen([sys.executable, SCRIPT, "--base", "--ref", "main", "--timeout", "2", replay_probe.write_text(work, "held-stdin.md", body("echo FAIL"))],
                                cwd=box.repository, env={**box.environment, "PATH": stand_in("reading", "cat > /dev/null")},
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            held.wait(timeout=LIMIT)
        except subprocess.TimeoutExpired:
            os.killpg(held.pid, signal.SIGKILL)
            held.wait()
        took = time.monotonic() - started
        out, err = held.stdout.read(), held.stderr.read()
        held.stdin.close()
        cases.step("held-stdin", took < LIMIT and held.returncode == 0 and "| base ok | FAIL |" in out, f"took {took:.0f} s, exit {held.returncode}, {out[-300:]} {err[-300:]}")
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

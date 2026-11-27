#!/usr/bin/env python3
"""Run run-criteria.py on a temporary git repository and print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS run limit` or
`FAIL run limit`, and exit 1 on any failure:
- `whole-limit`: a check that sleeps 30 s, then one that leaves a mark, under `--timeout 60 --run-timeout 3`; the run exits 1 within `LIMIT` seconds
  naming its whole limit, so the check running at it is cut short, and the second never starts;
- `cut-call`: `--base` with a `git archive` that never answers, under `--timeout 60 --run-timeout 3`; the run exits 1 within `LIMIT` seconds naming its
  whole limit, not the call's own;
- `under-limit`: two checks that each sleep 1 s, under `--run-timeout 60`; both pass and nothing names the whole limit;
- `progress`: `--hunks` on a branch adding a script with one `if`; stderr holds one line per reverted group and per mutant, each with its count,
  the file's place and the seconds since the run began, the last mutant's count equal to the total.

usage: replay-run-limit.py"""
import os
import pathlib
import re
import shutil
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
LIMIT = 20  # the 3 s limit with room for a loaded machine, and short of the 30 s a check would take uncut
TOOL = 'import sys\n\nif len(sys.argv) > 1:\n    print("ok")\n'


def body(*commands):
    return "## Definition of done\n\n" + "".join(f"{n}. [check] **Check {n} prints PASS**: `{command}` prints `PASS`; on base `FAIL`.\n"
                                                for n, command in enumerate(commands, 1))


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases("run limit")
    with replay_probe.scratch("run-limit-") as work:
        box = replay_probe.Sandbox(work)

        def run(case, *argv, text, **variables):
            started = time.monotonic()
            done = box.python(SCRIPT, *argv, replay_probe.write_text(work, f"{case}.md", text), timeout=120, **variables)
            return done, time.monotonic() - started

        mark = pathlib.Path(work, "second-started")
        done, took = run("whole-limit", "--timeout", "60", "--run-timeout", "3", text=body("sleep 30; echo PASS", f"touch {mark}; echo PASS"))
        cases.step("whole-limit", took < LIMIT and done.returncode == 1 and "run-criteria: the run passed its whole limit of 3 s" in done.stderr
                   and not mark.exists(), f"took {took:.0f} s, exit {done.returncode}, second check started: {mark.exists()}, {done.stdout[-200:]} {done.stderr[-300:]}")
        folder = pathlib.Path(work, "hung-git")
        folder.mkdir()
        replay_probe.write_text(folder, "git", f'#!/bin/sh\n[ "$1" = archive ] && {{ python3 -c "import time; time.sleep(60)" & wait; }}\nexec {shutil.which("git")} "$@"\n').chmod(0o755)
        done, took = run("cut-call", "--base", "--ref", "main", "--timeout", "60", "--run-timeout", "3", text=body("echo FAIL"),
                         PATH=f"{folder}{os.pathsep}{box.environment['PATH']}")
        cases.step("cut-call", took < LIMIT and done.returncode == 1 and "run-criteria: the run passed its whole limit of 3 s" in done.stderr,
                   f"took {took:.0f} s, exit {done.returncode}, {done.stderr[-300:]}")
        done, took = run("under-limit", "--run-timeout", "60", text=body("sleep 1; echo PASS", "sleep 1; echo PASS"))
        cases.step("under-limit", done.returncode == 0 and done.stdout.count("| pass | PASS |") == 2 and "whole limit" not in done.stderr,
                   f"exit {done.returncode}, {done.stdout[-300:]} {done.stderr[-300:]}")

        box.git("checkout", "-q", "-b", "change")
        replay_probe.write_text(box.repository, "tool.py", TOOL)
        box.git("add", "tool.py")
        box.git("commit", "-q", "-m", "Add the tool")
        done, _ = run("progress", "--hunks", "--ref", "main", text=body("python3 tool.py go | sed s/ok/PASS/"))
        lines = [line for line in done.stderr.splitlines() if line.startswith("run-criteria: ")]
        reverts = [line for line in lines if re.fullmatch(r"run-criteria: reverting 1 hunks of tool\.py, file 1 of 1, \d+ s", line)]
        mutants = [re.fullmatch(r"run-criteria: mutant (\d+) of (\d+) in tool\.py, file 1 of 1, \d+ s", line) for line in lines]
        counts = [(int(found[1]), int(found[2])) for found in mutants if found]
        cases.step("progress", len(reverts) == 1 and counts and [count for count, _ in counts] == list(range(1, counts[-1][1] + 1))
                   and len(reverts) + len(counts) == len(lines), f"exit {done.returncode}, {lines}, {done.stdout[-300:]}")
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

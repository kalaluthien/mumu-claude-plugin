#!/usr/bin/env python3
"""Run run-criteria.py `--hunks` on a temporary git repository whose change adds a script of surviving and killed mutants under three slow
checks of 1 s each, the first killing nothing and the last the most. Print `ok <case>` or `fail <case>: <detail>` per case, then `PASS` or
`FAIL`, and exit 1 on any failure:
- `same-findings-faster`: the sweep prints the summary, finding lines and exit status that the sweep of a923dc2f, which ran the checks of each
  revert and mutant one after another in order, printed for this change, in at most a third of the least time that sweep needs: three checks
  at the head and at least the first two for each of the 26 reverts and mutants, 55 runs of a check timed once on this machine now, so a
  loaded machine slows both sides; with `--jobs 1 --fresh` it prints the same and runs fewer checks than that sweep's 76, since the check
  that killed most runs first, and takes a second for each check it runs, since one job runs them one at a time;
- `second-sweep-replayed`: a second sweep of the same head runs no check, replays all 26 and prints the same summary and findings, while a
  sweep with `--fresh`, another `--timeout`, a reworded check, an edited file outside the repository that a check reads, a check that names
  a folder outside it, or after a committed edit to the data file the checks read, runs every revert and mutant again.
- `timeout-not-kept`: a mutant killed by a check that timed out is swept again by the next sweep, running one check, while the revert and the
  other two mutants are replayed.

usage: replay-hunk-speed.py"""
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
SERIAL_RUNS = 3 + 26 * 2
OLD_RUNS = 76  # the checks a923dc2f's sweep ran for this change, in order
CHECK = "{n}. [check] **The tool's check number {n} prints ok**: `sleep 1; echo run >> {counter}; {test} && echo ok` prints `ok`; on base nothing.\n"
TESTS = [
    "python3 -c pass",
    "python3 tool.py | grep -q .",
    'test "$(python3 tool.py)" = "big 5 True low 31"',
]
TOOL = '''LIMITS = (3, 10, 20)
SIZES = (1, 2, 4, 8, 16)


def grade(count):
    if count > LIMITS[0]:
        return "big"
    return "small"


def level(count):
    if count >= LIMITS[2] * 2:
        return "high"
    return "low"


words = open("data.txt").read().split()
print(grade(len(words)), len(words), len(words) >= 1, level(len(words) + 0), sum(SIZES))
'''
# its number made 1 sleeps past the timeout, so that mutant is killed by a timeout; 60 made 0 changes nothing and survives
SLOW = "import time\n\ntime.sleep(0 * 60)\nprint('hi')\n"
SLOW_CHECK = "## Definition of done\n\n1. [check] **The slow tool greets**: `echo run >> {counter}; python3 slow.py` prints `hi`; on base nothing.\n"
LINE = "tool.py:{}: surviving mutant: no criterion fails when the number `{}` becomes `{}`, so make a criterion fail on it or drop it"
OLD_LINES = sorted([
    "hunks: 1 reverted against main, 2 conditions made False, 23 mutants made, 6 unneeded",
    LINE.format(1, 3, 0), LINE.format(1, 10, 0), LINE.format(12, 2, 0), LINE.format(18, 1, 0), LINE.format(18, 0, 1),
    "tool.py:12: unneeded condition: no criterion reaches this branch, so drop it or make a criterion refuse through it",
])
FINDING = re.compile(r"^(hunks: .*|.*: (surviving mutant|unneeded (hunk|condition)).*)$", re.M)


def sweep(box, counter, *flags, tests=TESTS):
    """(exit code, summary and finding lines, seconds, checks run, all it printed) of a `--hunks` sweep whose checks run TESTS."""
    counter.write_text("")
    body = "## Definition of done\n\n" + "".join(CHECK.format(n=n, counter=counter, test=test) for n, test in enumerate(tests, 1))
    started = time.monotonic()
    done = box.python(SCRIPT, "--hunks", "--ref", "main", *flags, replay_probe.write_text(box.work, "body.md", body), timeout=900)
    seconds = time.monotonic() - started
    text = done.stdout + done.stderr
    return done.returncode, sorted(match[0] for match in FINDING.finditer(text)), seconds, len(counter.read_text().split()), text


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("hunk-speed-") as work:
        box = replay_probe.Sandbox(work, commit=False)
        (box.repository / "data.txt").write_text("one two three four five\n")
        box.git("add", "-A")
        box.git("commit", "-qm", "base")
        box.git("checkout", "-qb", "change")
        (box.repository / "tool.py").write_text(TOOL)
        box.git("add", "-A")
        box.git("commit", "-qm", "change")
        counter, outside, folder = work / "runs.txt", work / "outside.txt", work / "outside"
        outside.write_text("one\n")
        folder.mkdir()
        tests = [f"cat {outside} >/dev/null", *TESTS[1:]]
        after = sweep(box, counter, tests=tests)
        started = time.monotonic()
        replay_probe.sh("sh", "-c", f"sleep 1; {TESTS[1]}", cwd=box.repository, environment=box.environment)
        serial = SERIAL_RUNS * (time.monotonic() - started)
        alone = sweep(box, counter, "--jobs", "1", "--fresh", tests=tests)
        cases.step("same-findings-faster", after[:2] == alone[:2] == (1, OLD_LINES) and after[2] * 3 <= serial and alone[3] < OLD_RUNS and alone[3] <= alone[2],
                   f"{after[2]:.1f} s against {serial:.1f} s; {alone[3]} checks run in one job against {OLD_RUNS}\n{after[4]}")
        again = sweep(box, counter, tests=tests)
        runs = {"fresh": sweep(box, counter, "--fresh", tests=tests), "timeout": sweep(box, counter, "--timeout", "899", tests=tests),
                "reworded": sweep(box, counter, tests=[*tests[:2], "true && " + tests[2]])}
        outside.write_text("two\n")
        runs["outside file"] = sweep(box, counter, tests=tests)
        sweep(box, counter, tests=[f"ls {folder} >/dev/null", *TESTS[1:]])
        runs["outside folder"] = sweep(box, counter, tests=[f"ls {folder} >/dev/null", *TESTS[1:]])
        (box.repository / "data.txt").write_text("one two three four five\n\n")
        box.git("commit", "-qam", "data")
        runs["data edited"] = sweep(box, counter, tests=tests)
        swept = [name for name, run in runs.items() if run[3] < 26 + 3 * (name != "data edited")]
        cases.step("second-sweep-replayed", again[:2] == after[:2] and again[3] == 0 and "cached: 26 reverts and mutants replayed" in again[4]
                   and all(run[1][1:] == after[1][1:] for name, run in runs.items() if name != "data edited") and not swept,
                   f"again ran {again[3]} checks; swept too little: {swept}; " + ", ".join(f"{name} {run[3]}" for name, run in runs.items()) + f"\nagain:\n{again[4]}")
        slow = replay_probe.Sandbox(work / "slow")
        slow.git("checkout", "-qb", "change")
        (slow.repository / "slow.py").write_text(SLOW)
        slow.git("add", "-A")
        slow.git("commit", "-qm", "change")
        body = replay_probe.write_text(work, "slow.md", SLOW_CHECK.format(counter=counter))
        runs = []
        for _ in range(2):
            counter.write_text("")
            done = slow.python(SCRIPT, "--hunks", "--timeout", "3", "--ref", "main", body, timeout=300)
            runs.append((done.returncode, len(counter.read_text().split()), done.stdout + done.stderr))
        cases.step("timeout-not-kept", runs[0][0] == runs[1][0] and runs[1][1] == 1 and "cached: 3 reverts and mutants replayed" in runs[1][2],
                   f"checks run: {[run[1] for run in runs]}\n{runs[1][2]}")
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

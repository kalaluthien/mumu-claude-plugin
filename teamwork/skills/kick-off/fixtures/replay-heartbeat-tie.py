#!/usr/bin/env python3
"""Replay a manager's team losing its last worker and starting one again, on a scratch repository with a git board and the fake herdr, with the real heartbeat monitor running throughout for a set number of polls, and print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS` or `FAIL`.

Each cycle files an open task nobody holds while the manager has no worker (the second cycle with a sentinel alone), which the heartbeat must not print in the polls after it, then starts a worker, after which it must print that task's `route` line and again the first task's. A last case has the worker report on a root and leave at once, which the heartbeat must still feed to the manager before its polls end.

usage: replay-heartbeat-tie.py [--only off | --only on | --mutant] [--verbose]
`--only off` judges the quiet cases alone; `--only on` judges the resuming cases, which count only after the quiet ones passed, since a monitor that never stopped has nothing to resume; with neither, all cases are judged.
`--mutant` runs the monitor with its tie to live workers cut out, and prints `PASS` only when the cases fail on that copy and pass on the real one, which shows the cases fail when the tie is removed."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

MONITOR = ROOT / "monitors" / "print-team-gaps.py"
USE_BOARD = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
TIE = "team_names.watching(me, listed)"  # the gate the mutant replaces
POLLS = 50  # about twice the polls the steps below take, each of which waits on polls, never on a clock
QUIET_POLLS = 4  # whole polls in which a monitor that still watched would print the task
VERBOSE = False


def trial(monitor):
    """The cases of one run of MONITOR as {case: (passed, what it saw)}."""
    with replay_probe.scratch("heartbeat-tie-") as work:
        manager, worker = replay_probe.agent("x-manager", 1, "working"), replay_probe.agent("t-worker", 2)
        sandbox = replay_probe.Sandbox(work, [manager, worker])

        def file(title):
            done = sandbox.python(USE_BOARD, "file", "--title", title, "--body", replay_probe.write_text(work, "body.md", f"{title}.\n"), "--label", "scope:x", pane="w1:p1")
            if VERBOSE:
                print(f"$ use-board.py file {title}\n{done.stdout}{done.stderr}", file=sys.stderr)
            return done.stdout.strip().rsplit("/", 1)[-1].removesuffix(".json")

        def printed(number):
            return live.text().count(f"route #{number} ")

        first = file("Tie a first task")
        cases = {}
        with sandbox.monitor("w1:p1", POLLS, work / "monitor.log", monitor) as live:
            cases["start"] = (live.until(lambda: printed(first)), live.text())
            for cycle, others in ((1, []), (2, [replay_probe.agent("t-sentinel", 3)])):  # a sentinel is no worker, so it keeps the heartbeat off too
                before = printed(first)
                sandbox.herdr([manager, *others])  # the last worker is gone
                live.polls(1)
                number = file(f"Tie task {cycle}")
                cases[f"off-{cycle}"] = (live.polls(QUIET_POLLS) and not printed(number), live.text())
                sandbox.herdr([manager, *others, worker])  # a worker starts
                cases[f"on-{cycle}"] = (live.until(lambda: printed(number) and printed(first) > before), live.text())  # a gap printed before the stop prints again
            # the worker reports on a root and is gone before the next poll, which the one last read still feeds
            sandbox.python(USE_BOARD, "comment", first, "--reported", "the tie root landed.", pane="w1:p2")
            sandbox.herdr([manager])
            fed = live.until(lambda: f"feed #{first} " in live.text())
            code = live.end()
            cases["off-last-feed"] = (fed and code == 0, f"exit {code} after {POLLS} polls: {live.text()}")
    return cases


def verdict(cases, only):
    chosen = {name: result for name, result in cases.items() if only is None or name == "start" or name.startswith(only)}
    if only == "on":  # a monitor that never stopped passes every resuming case
        chosen |= {name: result for name, result in cases.items() if name.startswith("off")}
    return chosen


def show(cases):
    for name, (passed, saw) in cases.items():
        print(f"ok {name}" if passed else f"fail {name}: {' '.join(saw.split())[-1500:]}", flush=True)


def mutant_monitor(folder):
    """A copy of the monitor in FOLDER with the tie replaced by a constant true, beside a link to the plugin's lib, which the monitor finds by its own path."""
    source = MONITOR.read_text()
    if TIE not in source:
        return None
    (folder / "monitors").mkdir()
    (folder / "lib").symlink_to(ROOT / "lib")
    copy = folder / "monitors" / MONITOR.name
    copy.write_text(source.replace(TIE, "True"))
    return copy


def main(args):
    global VERBOSE
    flags = list(args)
    VERBOSE = "--verbose" in flags
    only = None
    if "--only" in flags:
        at = flags.index("--only")
        only = flags[at + 1] if at + 1 < len(flags) else None
        del flags[at:at + 2]
    flags = [flag for flag in flags if flag != "--verbose"]
    if only not in (None, "off", "on") or flags not in ([], ["--mutant"]) or flags and only:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    if flags:
        with replay_probe.scratch("heartbeat-mutant-") as folder:
            copy = mutant_monitor(folder)
            if copy is None:
                cases.step("mutant", False, f"{MONITOR.name} holds no {TIE}, so nothing can be cut out")
                return cases.finish()
            real, cut = trial(MONITOR), trial(copy)
        show(cut)
        cases.step("mutant", all(passed for passed, _ in real.values()) and not all(passed for passed, _ in cut.values()),
                   "the cases did not pass on the real monitor and fail on the cut copy")
        return cases.finish()
    chosen = verdict(trial(MONITOR), only)
    for name, (passed, saw) in chosen.items():
        cases.step(name, passed, saw)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

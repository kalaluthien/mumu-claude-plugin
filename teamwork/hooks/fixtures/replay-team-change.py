#!/usr/bin/env python3
"""Run `wait-team-change.py`, which the task pane waits on, in a sandbox, mark the tasks changed as team sessions do by touching the signal file, and print
`ok <case>` or `fail <case>: <the lines it saw>` per case, then `PASS team change` or `FAIL team change`, exiting 1 on any failure.

usage: replay-team-change.py
- first: one `changed` comes at start, before any mark;
- burst: three touches a moment apart give one more `changed`, and no other once the file has stayed quiet past the script's QUIET;
- deleted: deleting the file gives one more `changed`, and a touch after that gives another, so the watch outlives the file it watched."""
import pathlib
import sys
import time

HOOKS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS.parent / "lib"))
import replay_probe  # noqa: E402

WATCHER = HOOKS / "wait-team-change.py"
QUIET = 2  # wait-team-change.py's seconds without a mark that end a burst
WAIT_SECONDS = 10  # seconds a wanted line may take


def lines(log, count):
    """The `changed` lines in LOG once COUNT have come or WAIT_SECONDS passed; then QUIET seconds more, so a line too many shows too."""
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline and log.read_text().count("changed") < count:
        time.sleep(0.1)
    time.sleep(QUIET + 0.5)
    return log.read_text().split()


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases("team change")
    with replay_probe.scratch("team-change-") as work:
        sandbox = replay_probe.Sandbox(work)
        signal = pathlib.Path(sandbox.environment["CLAUDE_CONFIG_DIR"]) / "teamwork" / "tasks-changed"
        log = work / "watch.log"
        watcher = sandbox.start([sys.executable, WATCHER], log)
        try:
            seen = lines(log, 1)
            cases.step("first", seen == ["changed"] and signal.exists(), f"{seen}, signal file there: {signal.exists()}")
            for _ in range(3):
                signal.touch()
                time.sleep(0.3)
            seen = lines(log, 2)
            cases.step("burst", seen == ["changed"] * 2, seen)
            signal.unlink()
            deleted = lines(log, 3)
            signal.touch()
            seen = lines(log, 4)
            cases.step("deleted", deleted == ["changed"] * 3 and seen == ["changed"] * 4, f"after the delete {deleted}, after the touch {seen}")
        finally:
            watcher.kill()
            watcher.wait()
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

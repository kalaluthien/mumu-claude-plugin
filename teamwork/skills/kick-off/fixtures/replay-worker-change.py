#!/usr/bin/env python3
"""Replay a held task changing under a live worker, on a scratch repository with a git board and the fake herdr, with the real heartbeat monitor run as that worker for a set number of polls, and print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS` or `FAIL`.

Cases: `start`, a task the worker already holds prints no `changed` line in its first polls; `decision`, a manager's `DECIDED:` on it prints one, which names `holders`; `second`, a decision in the poll after a printed one prints its own line; `report`, the worker's own `REPORTED:` prints none in the polls after it; and `lost`, a `holders` change to another session prints a `changed` line and then `holds nothing`; the monitor ends by itself after its polls.

usage: replay-worker-change.py"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

USE_BOARD = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
POLLS = 30  # about twice the polls the steps below take, each of which waits on polls, never on a clock
QUIET_POLLS = 3  # polls in which a monitor that wrongly printed would show


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("worker-change-") as work:
        sandbox = replay_probe.Sandbox(work, [replay_probe.agent("c-manager", 1, "working"), replay_probe.agent("c-worker", 2, "working")])

        def use(pane, *argv):
            return sandbox.python(USE_BOARD, *argv, pane=pane).stdout.strip()

        def changes():
            return live.text().count(f"changed #{number} ")

        def quiet():
            """Whether the monitor went through QUIET_POLLS whole polls after now, a worker's poll listing the sessions once."""
            began = live.lists()
            return live.until(lambda: live.lists() > began + QUIET_POLLS)

        number = use("w1:p1", "file", "--title", "Change a held task", "--body", replay_probe.write_text(work, "body.md", "Change a held task.\n"), "--label", "scope:x").rsplit("/", 1)[-1].removesuffix(".json")
        use("w1:p1", "decide", number, "--decision", "c-worker holds this.", "--holders", "c-worker")
        with sandbox.monitor("w1:p2", POLLS, work / "monitor.log") as live:
            cases.step("start", quiet() and changes() == 0, live.text())
            use("w1:p1", "decide", number, "--decision", "use the other way.")
            cases.step("decision", live.until(lambda: changes() >= 1) and "`holders`" in live.text(), live.text())
            use("w1:p1", "decide", number, "--decision", "and keep the old name.")
            cases.step("second", live.until(lambda: changes() >= 2), live.text())  # a change in the poll after a printed one is its own line
            use("w1:p2", "comment", number, "--reported", "criteria at 0123abc")
            cases.step("report", quiet() and changes() == 2, live.text())
            use("w1:p1", "decide", number, "--decision", "c-other holds this.", "--holders", "c-other")
            lost = live.until(lambda: changes() >= 3 and "holds nothing" in live.text())  # the task is open and names another session
            code = live.end()
            cases.step("lost", lost and code == 0, f"exit {code} after {POLLS} polls: {live.text()}")
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

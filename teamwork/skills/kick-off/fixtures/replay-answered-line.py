#!/usr/bin/env python3
"""Replay a held task whose question a manager answered, on a scratch repository with a git board and the fake herdr, with the real heartbeat monitor run as that worker for a few polls, and print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS` or `FAIL`.

Cases: `unacted`, a run with the answer the worker has not acted on prints one `answered` line; and `acted`, a run after the worker's own `REPORTED:` comment on the task prints none.

usage: replay-answered-line.py"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

USE_BOARD = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
MONITOR = ROOT / "monitors" / "print-team-gaps.py"
POLLS = "4"  # a line wrongly printed again would show in a later poll


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("answered-line-") as work:
        sandbox = replay_probe.Sandbox(work, [replay_probe.agent("c-manager", 1, "working"), replay_probe.agent("c-worker", 2, "working")])

        def use(pane, *argv):
            return sandbox.python(USE_BOARD, *argv, pane=pane).stdout.strip()

        def heartbeat():
            done = sandbox.python(MONITOR, "--polls", POLLS, pane="w1:p2", timeout=60, TEAMWORK_MONITOR_POLL="0.1")
            return done.returncode == 0, done.stdout + done.stderr

        number = use("w1:p1", "file", "--title", "Answer a held task", "--body", replay_probe.write_text(work, "body.md", "Answer a held task.\n"), "--label", "scope:x").rsplit("/", 1)[-1].removesuffix(".json")
        use("w1:p1", "decide", number, "--decision", "c-worker holds this.", "--holders", "c-worker")
        asked = use("w1:p2", "comment", number, "--blocked", "which way")
        use("w1:p1", "decide", number, "--decision", "take the first way.", "--by", "c-manager", "--answers", asked)
        ended, saw = heartbeat()
        cases.step("unacted", ended and saw.count(f"answered #{number}") == 1, saw)
        use("w1:p2", "comment", number, "--reported", "took the first way")
        ended, saw = heartbeat()
        cases.step("acted", ended and f"answered #{number}" not in saw, saw)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Replay a reopened task whose questions were answered on a board read from another checkout path, and print `PASS` when the manager's heartbeat
there names only the question still open, else `FAIL` with what it named. A task holds a question asked and left open, then one a manager answered
and one an owner answered; it is resolved and reopened, and the board is copied to a second repository, where the answers' urls name the first
one's git dir; print-team-gaps.py polls once there as the manager, beside the worker that holds the task.

usage: replay-reopen-ask.py"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
USE = HERE.parent / "scripts" / "use-board.py"
GAPS = ROOT / "monitors" / "print-team-gaps.py"
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("reopen-ask-") as work:
        sandbox = replay_probe.Sandbox(work, [replay_probe.agent("x-manager", 1), replay_probe.agent("w-worker", 2)])
        first, second = sandbox.repository, sandbox.init(work / "second")

        def use(*argv, **options):
            return sandbox.python(USE, *map(str, argv), pane="w1:p1", **options).stdout.strip()

        def text(name, body):
            return replay_probe.write_text(work, name, body)

        number = use("file", "--title", "Probe a reopened task", "--body", text("body.md", "Probe.\n"), "--label", "scope:x").rsplit("/", 1)[-1]
        use("hold", number, "--holders", "w-worker")
        again = use("comment", number, "--blocked", "which way now?")
        manager_ask = use("comment", number, "--blocked", "which way?")
        owner_ask = use("comment", number, "--blocked", "merge it?", "--asks", "owner", "--option", "yes", "--option", "no")
        use("decide", number, "--decision", "the first way", "--answers", manager_ask)
        owner, said = sandbox.decider("owner", "merge it", "x-manager")
        use("decide", number, "--decision", "merge", *said, "--answers", owner_ask, **owner)
        use("resolve", number, "--summary", "done")
        use("reopen", number)
        sandbox.git("fetch", "-q", first, "refs/teamwork-blackboard:refs/teamwork-blackboard", cwd=second)
        heartbeat = sandbox.python(GAPS, "--polls", "1", pane="w1:p1", cwd=second)
    named = [line for line in heartbeat.stdout.splitlines() if line.startswith("answer #")]
    if heartbeat.returncode != 0 or len(named) != 1 or again.partition("refs/teamwork-blackboard/")[2] not in named[0]:
        return replay_probe.fail(f"exit {heartbeat.returncode}: " + " | ".join(named or [heartbeat.stdout + heartbeat.stderr]))
    return replay_probe.Cases().finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Replay the manager heartbeat's `rebalance` lines on a scratch repository with a git board and the fake herdr, with the real heartbeat monitor run as the manager for
a few polls, and print `ok <case>` or `fail <case>: <what it saw>` per case, then `PASS` or `FAIL`; exit 1 on any fail:
- queue-of-3: a worker that holds 3 tasks, each waiting on an open task, gets one `rebalance` line naming the worker and the 3 tasks, and saying 3 of 4 live workers;
- shared-file: a task that waits on an open task only for a file both cover, its body naming no such task, gets a `rebalance` line naming both tasks and the file;
- queue-of-2: a worker that holds 2 tasks that wait for a needed result, the body naming the task it needs, gets no `rebalance` line;
- rule-named: each line names the manager playbook's Rebalance rule, and `references/manager.md` holds that rule with the cap of 4 live workers;
- at-cap: with 4 live workers a `rebalance` line for a queue of 3 says the team is at the cap and asks the owner.

usage: replay-rebalance-lines.py"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

USE = ROOT / "skills" / "kick-off" / "scripts" / "use-board.py"
manager = replay_probe.agent("x-manager", 1, "working")


class Team:
    def __init__(self, work, name):
        self.work = work
        self.sandbox = replay_probe.Sandbox(work / name, [manager])

    def file(self, title, text, holder=None, depends=()):
        body = replay_probe.write_text(self.sandbox.work, "body.md", text)
        done = self.sandbox.python(USE, "file", "--title", title, "--body", body, "--label", "scope:x", "--depends", " ".join(depends))
        number = done.stdout.strip().rsplit("/", 1)[-1].removesuffix(".json")
        if holder:
            self.sandbox.python(USE, "hold", number, "--holders", holder)
        return number

    def lines(self, *agents):
        self.sandbox.herdr([manager, *agents])
        done = self.sandbox.python(replay_probe.MONITOR, "--polls", 3, pane="w1:p1", timeout=120, TEAMWORK_MONITOR_POLL="0.1")
        return [line for line in done.stdout.splitlines() if line.startswith("rebalance ")] + ([] if done.returncode == 0 else [f"exit {done.returncode}: {done.stderr}"])


def criterion(file, after="", more=""):
    return (f"Probe a rebalance.\n\n## Definition of done\n\n1. [check] **The probe script prints its result for this task**: `sh -c 'python3 {file} && echo PASS || echo FAIL'` prints `PASS`; "
            f"on base `FAIL`. covers: `{file}{more}`{after}\n")


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("rebalance-lines-") as work:
        team = Team(work, "queue")
        head = team.file("Probe the head", criterion("a.py"), holder="busy-worker")
        queued = [team.file(f"Probe a queued task {n}", criterion(f"q{n}.py", after=f" after #{head}"), holder="q-worker", depends=[head]) for n in (1, 2, 3)]
        free = team.file("Probe a free task", criterion("free.py"), holder="q-worker")
        three = team.lines(replay_probe.agent("busy-worker", 2, "working"), replay_probe.agent("q-worker", 3, "working"), replay_probe.agent("c-worker", 4, "idle"),
                           replay_probe.agent("watch-sentinel", 6, "idle"))
        cases.step("queue-of-3", len(three) == 1 and all(f"#{n}" in three[0] for n in queued) and "q-worker" in three[0] and "3 of 4 live workers" in three[0]
               and f"#{free}" not in three[0], "\n".join(three))
        rule = (ROOT / "skills" / "kick-off" / "references" / "manager.md").read_text()
        cases.step("rule-named", all("Rebalance rule" in line for line in three) and three and "**Rebalance**" in rule and "up to 4 live workers per team" in rule, "\n".join(three))
        capped = team.lines(replay_probe.agent("busy-worker", 2, "working"), replay_probe.agent("q-worker", 3, "working"), replay_probe.agent("c-worker", 4, "idle"), replay_probe.agent("d-worker", 5, "idle"))
        cases.step("at-cap", len(capped) == 1 and "at the cap of 4" in capped[0] and "ask the owner" in capped[0], "\n".join(capped))

        team = Team(work, "shared")
        first = team.file("Probe the first", criterion("same.py", more=", also.py"), holder="one-worker")
        second = team.file("Probe the second", criterion("same.py", more=", also.py"), holder="two-worker", depends=[first])
        gone = team.file("Probe a task not planned", criterion("same.py"))
        team.sandbox.python(USE, "resolve", gone, "--summary", "not wanted", "--not-planned")
        team.file("Probe the third", criterion("same.py"), holder="three-worker", depends=[gone])
        shared = team.lines(replay_probe.agent("one-worker", 2, "working"), replay_probe.agent("two-worker", 3, "working"), replay_probe.agent("three-worker", 4, "working"))
        cases.step("shared-file", len(shared) == 1 and f"#{second}" in shared[0] and f"#{first}" in shared[0] and "also.py, same.py" in shared[0], "\n".join(shared))

        team = Team(work, "pair")
        head = team.file("Probe the needed result", criterion("n.py"), holder="n-worker")
        for number in (1, 2):
            team.file(f"Probe a needing task {number}", criterion(f"p{number}.py", after=f" once #{head} lands"), holder="p-worker", depends=[head])
        two = team.lines(replay_probe.agent("n-worker", 2, "working"), replay_probe.agent("p-worker", 3, "working"))
        cases.step("queue-of-2", not two, "\n".join(two))
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Replay the heartbeat's lines that a read of the sessions or the board made as the lines are made must hide, on a scratch repository with a git board and landing and the fake herdr,
with the real heartbeat monitor run for a set number of polls, and print `ok <case>` or `fail <case>: <what it saw>` per case; exit 1 on any fail. Cases:
- started-late: no `route` line for a task held by a worker that the poll's first read of the sessions missed and the second lists, since the sessions are read again when the lines are made (#1365)
- read-failed: no `route` line when that second read fails, since the host failed to answer
- unheld: one `route` line for a task no live worker holds, so the guard hides no real gap
- idle-moved, blocked-moved: no `idle` or `blocked` line for a worker the second read shows working, and the line when it does not
- idle-held, merged-held, holds-held: an `idle`, `merged` or `holds nothing` line goes the poll a task is held by a write no team session signals, which leaves the kept read of the board as it was,
  and prints again once that task is let go, since the board is read again before such a line
- rebase-clean: a `rebase` line goes the poll a git move the kept read predates makes the change clean, and prints again once it conflicts again

usage: replay-route-lines.py
It prints `PASS` last when every case passed, else `FAIL`."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))
import replay_probe  # noqa: E402

SCRIPTS = ROOT / "skills" / "kick-off" / "scripts"
USE_LANDING = SCRIPTS.parent / "references" / "adapters" / "landing-git" / "scripts" / "use-landing.py"
PROMPT = "Do you want to proceed?\n❯ 1. Yes\n  2. No\nEsc to cancel"
POLLS = 20  # about twice the polls a case below takes, each step of which waits on polls, never on a clock
manager = replay_probe.agent("x-manager", 1, "working")


class Team:
    def __init__(self, work):
        self.work, self.sandbox = work, replay_probe.Sandbox(work, [manager])
        self.runs = 0

    def use(self, *argv, pane="w1:p1", **variables):
        return self.sandbox.python(SCRIPTS / "use-board.py", *argv, pane=pane, **variables).stdout.strip()

    def file(self, title, holder=None):
        number = self.use("file", "--title", title, "--body", replay_probe.write_text(self.work, "body.md", "Probe the route line.\n"), "--label", "scope:x").rsplit("/", 1)[-1].removesuffix(".json")
        if holder:
            self.use("hold", number, "--holders", holder)
        return number

    def outside(self, *argv):
        """A board write no team session signals, as the owner's on the web, so a heartbeat keeps the board it read before it."""
        return self.use(*argv, CLAUDE_CONFIG_DIR=self.work / "outside")

    def heartbeat(self, kind, pane="w1:p1", polls=1):
        """The lines starting with KIND that the monitor of PANE printed in POLLS polls, and its exit when not 0."""
        done = self.sandbox.python(replay_probe.MONITOR, "--polls", polls, pane=pane, timeout=60, TEAMWORK_MONITOR_POLL="0.1")
        return [line for line in done.stdout.splitlines() if line.startswith(kind)] + ([] if done.returncode == 0 else [f"exit {done.returncode}: {done.stderr}"])

    def twice(self, kind, pane, hide, show):
        """The lines starting with KIND that the monitor of PANE printed while HIDE, then SHOW, ran, each once a line was out and a whole poll later."""
        self.runs += 1
        with self.sandbox.monitor(pane, POLLS, self.work / f"monitor-{self.runs}.log") as live:

            def whole_poll():
                # a poll lists the sessions once, and once more before a line, so five more lists hold one whole poll after now
                began = live.lists()
                live.until(lambda: live.lists() >= began + 5)

            live.until(lambda: kind in live.text())
            hide()
            whole_poll()
            show()
            whole_poll()
            code = live.end()
        return [line for line in live.text().splitlines() if line.startswith(kind)] + ([] if code == 0 else [f"exit {code}"])

def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("route-lines-") as work:
        team = Team(work)
        sandbox = team.sandbox
        held, free = team.file("Probe a late worker", holder="late-worker"), team.file("Probe a free task")
        # the late worker's tab is not open yet, and the poll's first list misses it while the second shows it
        sandbox.herdr([manager, replay_probe.agent("other-worker", 3, "working"), replay_probe.agent("late-worker", 2, "working", hidden=2)])
        sandbox.state.write_text(json.dumps({**sandbox.herdr_state(), "tabs": [tab for tab in sandbox.herdr_state()["tabs"] if tab["label"] != "late-worker"]}))
        out = team.heartbeat("route")
        cases.step("started-late", not [line for line in out if line.startswith(f"route #{held} ")] and out, out)
        cases.step("unheld", len([line for line in out if line.startswith(f"route #{free} ")]) == 1 and len(out) == 1, out)

        sandbox.herdr([manager, replay_probe.agent("other-worker", 3, "working")])
        # a herdr whose list fails after the poll's first, as a host that stops answering does
        replay_probe.write_text(sandbox.bin, "herdr", f'#!/bin/sh\nif [ "$1 $2" = "agent list" ]; then\n  echo x >> "{work / "lists"}"\n'
                                f'  [ "$(wc -l < "{work / "lists"}")" -gt 1 ] && exit 1\nfi\nexec "{replay_probe.FAKE_HERDR / "herdr"}" "$@"\n').chmod(0o755)
        out = team.heartbeat("route")
        (sandbox.bin / "herdr").unlink()
        cases.step("read-failed", not out and (work / "lists").read_text().count("x") == 2, out)
        team.use("resolve", held, "--not-planned", "--summary", "REPORTED: probe done.")
        team.use("resolve", free, "--not-planned", "--summary", "REPORTED: probe done.")

        for kind, status in (("idle", "idle"), ("blocked", "blocked")):
            moving = replay_probe.agent("w-worker", 2, status, screen=PROMPT if status == "blocked" else "")
            sandbox.herdr([manager, moving])
            shown = team.heartbeat(kind)
            sandbox.herdr([manager, {**moving, "flip": status}])  # working at the second list
            hidden = team.heartbeat(kind)
            cases.step(f"{kind}-moved", len(shown) == 1 and not hidden, shown + ["--"] + hidden)

        sandbox.git("switch", "-q", "-c", "m-worker")
        sandbox.git("commit", "-q", "--allow-empty", "-m", "the probe change")
        sandbox.git("switch", "-q", "main")
        change = sandbox.python(USE_LANDING, "change", "m-worker", "Probe a change", replay_probe.write_text(work, "change.md", "Probe it.\n")).stdout.strip().rsplit("/", 1)[-1].removesuffix(".json")
        merged = sandbox.python(USE_LANDING, "merge", change, sandbox.git("rev-parse", "m-worker").strip())
        sandbox.herdr([manager, replay_probe.agent("i-worker", 4, "idle"), replay_probe.agent("m-worker", 3, "working")])
        taken = team.file("Probe a task taken after the poll")
        seen = team.twice("idle", "w1:p1", lambda: team.outside("hold", taken, "--holders", "i-worker"), lambda: team.outside("hold", taken, "--holders", ""))
        cases.step("idle-held", len(seen) == 2 and all(line.startswith("idle i-worker") for line in seen), seen)
        seen = team.twice("merged", "w1:p1", lambda: team.outside("hold", taken, "--holders", "m-worker"), lambda: team.outside("hold", taken, "--holders", ""))
        cases.step("merged-held", len(seen) == 2 and all(line.startswith(f"merged #{change} by m-worker") for line in seen), [merged.stderr] + seen)

        sandbox.herdr([manager, replay_probe.agent("h-worker", 5, "working")])
        seen = team.twice("holds nothing", "w1:p5", lambda: team.outside("hold", taken, "--holders", "h-worker"), lambda: team.outside("hold", taken, "--holders", ""))
        cases.step("holds-held", len(seen) == 2, seen)

        team.use("hold", taken, "--holders", "h-worker")
        replay_probe.write_text(sandbox.repository, "shared.txt", "base\n")
        sandbox.git("add", "shared.txt")
        sandbox.git("commit", "-q", "-m", "a shared file")
        sandbox.git("switch", "-q", "-c", "h-worker")
        sandbox.git("commit", "-q", "--allow-empty", "-m", "a clean change")
        clean = sandbox.git("rev-parse", "HEAD").strip()
        replay_probe.write_text(sandbox.repository, "shared.txt", "the worker's\n")
        sandbox.git("commit", "-q", "-am", "a conflicting change")
        sandbox.git("switch", "-q", "main")
        replay_probe.write_text(sandbox.repository, "shared.txt", "the base's\n")
        sandbox.git("commit", "-q", "-am", "the base moves")
        sandbox.python(USE_LANDING, "change", "h-worker", "Probe a conflict", replay_probe.write_text(work, "change.md", "Probe it.\n"))
        conflicting = sandbox.git("rev-parse", "h-worker").strip()
        seen = team.twice("rebase", "w1:p5", lambda: sandbox.git("branch", "-f", "h-worker", clean), lambda: sandbox.git("branch", "-f", "h-worker", conflicting))
        cases.step("rebase-clean", len(seen) == 2, seen)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

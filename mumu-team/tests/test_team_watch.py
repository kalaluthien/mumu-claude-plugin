"""`team-watch.py` run as the monitor runs it, in a lead's checkout, against a fake herdr and gh whose answers change per poll.

Run: python3 -m unittest discover mumu-team/tests
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

BIN = pathlib.Path(__file__).resolve().parent.parent / "bin"

# One fake for both tools: poll i reads `<tool>.<i>` (else the highest one below it); a file holding `FAIL` exits 1.
# gh answers only the issues whose kind its arguments name, as `kind:<kind>`.
FAKE = r'''#!/usr/bin/env python3
import json, os, pathlib, re, sys
d, tool = pathlib.Path(os.environ["FAKE"]), pathlib.Path(sys.argv[0]).name
count = d / f"{tool}.count"
i = int(count.read_text()) if count.exists() else 0
count.write_text(str(i + 1))
answer = max((p for p in d.glob(f"{tool}.[0-9]*") if int(p.suffix[1:]) <= i), key=lambda p: int(p.suffix[1:]), default=None)
text = answer.read_text() if answer else "[]"
if text.strip() == "FAIL":
    sys.exit(1)
if tool == "gh":
    a = sys.argv[1:]
    kinds = set(re.findall(r"kind:(\w+)", " ".join(a)))
    text = json.dumps([{"url": i["url"]} for i in json.loads(text) if i["kind"] in kinds])
print(text)
'''


class TeamWatch(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.checkout = self.tmp / "repo"
        (self.checkout / ".claude" / "worktrees").mkdir(parents=True)
        for tool in ("herdr", "gh"):
            (self.tmp / tool).write_text(FAKE)
            (self.tmp / tool).chmod(0o755)

    def herdr(self, poll, *agents):
        """herdr's answer from poll `poll` on: `(name, status, in this checkout)` per agent, or `FAIL`."""
        text = "FAIL" if agents == ("FAIL",) else json.dumps({"result": {"agents": [
            {"name": n, "agent_status": s, "cwd": str(self.checkout / ".claude" / "worktrees" / n if mine else self.tmp / "other" / n)}
            for n, s, mine in agents]}})
        (self.tmp / f"herdr.{poll}").write_text(text)

    def goals(self, poll, *urls, kind="goal"):
        """The open parentless issues from poll `poll` on, each of `kind`, or `FAIL`."""
        (self.tmp / f"gh.{poll}").write_text("FAIL" if urls == ("FAIL",) else json.dumps([{"url": u, "kind": kind} for u in urls]))

    def run_watch(self, ticks, idle="1000", role=None):
        env = dict(os.environ, FAKE=str(self.tmp), PATH=f"{self.tmp}:{os.environ['PATH']}",
                   MONITOR_POLL="0.01", MONITOR_TICKS=str(ticks), TEAM_WATCH_IDLE=idle)
        env.pop("MUMU_ROLE", None)
        if role:
            env["MUMU_ROLE"] = role
        done = subprocess.run([sys.executable, str(BIN / "team-watch.py")], cwd=self.checkout, env=env,
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.splitlines()

    def polls(self, tool):
        count = self.tmp / f"{tool}.count"
        return int(count.read_text()) if count.exists() else 0

    def test_no_goals_runs_every_poll_silently(self):
        self.herdr(0)
        self.goals(0)
        self.assertEqual(self.run_watch(ticks=30, idle="0"), [])
        self.assertEqual(self.polls("herdr"), 30)

    def test_a_failing_call_skips_one_poll_and_the_loop_goes_on(self):
        self.herdr(0, ("fix-a-12-1", "working", True))
        self.herdr(3, "FAIL")
        self.herdr(4, ("fix-a-12-1", "blocked", True))
        self.goals(0, "FAIL")
        self.assertEqual(self.run_watch(ticks=8, idle="0"), ["blocked fix-a-12-1"])
        self.assertEqual(self.polls("herdr"), 8)

    def test_each_worker_state_change_prints_one_line(self):
        self.herdr(0, ("fix-a-12-1", "working", True), ("other-lead-9-1", "idle", False), ("repo-lead", "idle", True))
        self.herdr(2, ("fix-a-12-1", "blocked", True), ("other-lead-9-1", "blocked", False))
        self.herdr(4, ("fix-a-12-1", "unknown", True))
        self.herdr(6, ("fix-a-12-1", "working", True))
        self.herdr(8)
        self.assertEqual(self.run_watch(ticks=10), ["blocked fix-a-12-1", "working fix-a-12-1", "gone fix-a-12-1"])

    def test_no_working_worker_for_the_idle_period_prints_one_idle_line(self):
        self.herdr(0, ("fix-a-12-1", "idle", True))
        self.goals(0, "https://github.com/o/r/issues/7")
        lines = self.run_watch(ticks=20, idle="0.05")
        self.assertEqual(lines[0], "idle fix-a-12-1")
        self.assertEqual(lines[1:], ["team idle 0m"])

    def test_a_root_task_alone_prints_the_idle_line(self):
        self.herdr(0, ("fix-a-12-1", "idle", True))
        self.goals(0, "https://github.com/o/r/issues/8", kind="task")
        self.assertEqual(self.run_watch(ticks=20, idle="0.05")[1:], ["team idle 0m"])
        self.goals(0, "https://github.com/o/r/issues/9", kind="backlog")
        self.assertEqual(self.run_watch(ticks=20, idle="0.05")[1:], [])

    def test_a_working_worker_prints_no_idle_line(self):
        self.herdr(0, ("fix-a-12-1", "working", True))
        self.goals(0, "https://github.com/o/r/issues/7")
        self.assertEqual(self.run_watch(ticks=20, idle="0"), [])

    def test_in_a_worker_session_it_exits_at_once(self):
        self.herdr(0, ("fix-a-12-1", "blocked", True))
        self.assertEqual(self.run_watch(ticks=0, role="worker"), [])
        self.assertEqual(self.polls("herdr"), 0)


if __name__ == "__main__":
    unittest.main()

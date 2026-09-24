"""Each line the `worker-watch` and `lead-heartbeat` monitors print, from their pure steps and from the scripts run against a fake herdr.

Run: python3 -m unittest discover mumu-team/tests
"""
import importlib.machinery
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

BIN = pathlib.Path(__file__).resolve().parent.parent / "bin"


def load(name):
    return importlib.machinery.SourceFileLoader(name.replace("-", "_"), str(BIN / (name + ".py"))).load_module()


watch, lead = load("worker-watch"), load("lead-heartbeat")
PARENT = "https://github.com/o/r/issues/1"
URL = "https://github.com/o/r/issues/7"
LEAD = f"Goal: g\nMission: leader of {PARENT}\nExpect: e\n"
MISSION = LEAD + f"Worker: a-7 {URL}\n"


def run(states, stuck_after=1800):
    """Feed one herdr status per tick (None: not listed) to worker-watch's step; return each tick's lines and due names."""
    state, words, out = {}, {}, []
    for now, word in states:
        agents = {} if word is None else {"a-7": word}
        words = watch.team.words(words, {"a-7": URL}, agents)
        state, lines, due = watch.step(state, {"a-7": URL}, words, now, stuck_after)
        out.append((lines, due))
    return out


def beats(ticks, after=1200):
    """Feed `(now, any worker working)` to lead-heartbeat's step; return whether each tick prints."""
    state, out = (None, None), []
    for now, working in ticks:
        state, due = lead.step(state, working, now, after)
        out.append(due)
    return out


class WorkerWatchStep(unittest.TestCase):
    def test_working_worker_prints_nothing(self):
        self.assertEqual(run([(0, "working"), (10, "working")]), [([], []), ([], [])])

    def test_blocked_prints_once(self):
        out = run([(0, "working"), (10, "blocked"), (20, "blocked")])
        self.assertEqual([o[0] for o in out], [[], [f"blocked a-7 {URL}"], []])

    def test_gone_prints_once(self):
        out = run([(0, "working"), (10, None), (20, None)])
        self.assertEqual([o[0] for o in out], [[], [f"gone a-7 {URL}"], []])

    def test_idle_and_back_to_work(self):
        out = run([(0, "working"), (10, "idle"), (20, "done"), (30, "working")])
        self.assertEqual([o[0] for o in out], [[], [f"idle a-7 {URL}"], [], [f"working a-7 {URL}"]])

    def test_unknown_keeps_the_last_word(self):
        out = run([(0, "idle"), (10, "unknown"), (20, "idle")])
        self.assertEqual([o[0] for o in out], [[f"idle a-7 {URL}"], [], []])

    def test_stuck_due_after_threshold_then_at_most_hourly(self):
        ticks = [(0, "idle"), (1799, "idle"), (1800, "idle"), (3000, "idle"), (5399, "idle"), (5400, "idle")]
        self.assertEqual([o[1] for o in run(ticks)], [[], [], ["a-7"], [], [], ["a-7"]])

    def test_work_resets_the_idle_clock(self):
        ticks = [(0, "idle"), (1000, "working"), (1100, "idle"), (2800, "idle"), (2900, "idle")]
        self.assertEqual([o[1] for o in run(ticks)], [[], [], [], [], ["a-7"]])

    def test_blocked_is_never_stuck(self):
        self.assertEqual([o[1] for o in run([(0, "blocked"), (9999, "blocked")])], [[], []])


class HeartbeatStep(unittest.TestCase):
    def test_quiet_team_beats_after_threshold_then_at_most_hourly(self):
        ticks = [(0, False), (1199, False), (1200, False), (2000, False), (4799, False), (4800, False)]
        self.assertEqual(beats(ticks), [False, False, True, False, False, True])

    def test_any_working_worker_silences_and_restarts_the_count(self):
        ticks = [(0, False), (1000, True), (1100, False), (2299, False), (2300, False)]
        self.assertEqual(beats(ticks), [False, False, False, False, True])

    def test_working_team_never_beats(self):
        self.assertEqual(beats([(0, True), (9999, True)]), [False, False])


class Team(unittest.TestCase):
    def test_reading(self):
        read = lead.team.read_mission
        self.assertEqual(read(MISSION), (PARENT, {"a-7": URL}))
        self.assertEqual(read(MISSION + "Worker: half\n"), (PARENT, {"a-7": URL}))
        self.assertEqual(read(LEAD), (PARENT, {}))
        self.assertIsNone(read(f"Goal: g\nMission: worker on {URL}\n"))

    def test_words_hold_the_last_word_on_unknown_for_both_monitors(self):
        words = lead.team.words
        workers = {"a-7": URL, "b-8": URL}
        self.assertEqual(words({}, workers, {"a-7": "unknown"}), {"a-7": "working", "b-8": "gone"})
        self.assertEqual(words({"a-7": "idle"}, workers, {"a-7": "unknown", "b-8": "done"}), {"a-7": "idle", "b-8": "idle"})


class Scripts(unittest.TestCase):
    """The loops, run with a fake `herdr` and `gh` on PATH and every threshold at zero."""

    def launch(self, script, mission, herdr_status, issue_state="OPEN", then=None, ticks="20"):
        """Fake herdr answers `herdr_status` first and `then` (default the same) from its second call on."""
        tmp = self.tmp = pathlib.Path(tempfile.mkdtemp())
        (tmp / "mission").mkdir()
        if mission is not None:
            (tmp / "mission" / "s1.md").write_text(mission)
        def listing(word):
            agents = [] if word is None else [{"name": "a-7", "agent_status": word}]
            return json.dumps({"result": {"agents": agents}})
        (tmp / "herdr").write_text(
            f"#!/bin/sh\nif [ -e {tmp}/herdr-called ]; then echo '{listing(then or herdr_status)}'; "
            f"else touch {tmp}/herdr-called; echo '{listing(herdr_status)}'; fi\n")
        (tmp / "gh").write_text(f"#!/bin/sh\necho {issue_state}\n")
        for f in ("herdr", "gh"):
            (tmp / f).chmod(0o755)
        env = dict(os.environ, PATH=f"{tmp}:{os.environ['PATH']}", CLAUDE_CODE_SESSION_ID="s1",
                   MONITOR_POLL="0.05", MONITOR_TICKS=ticks, WORKER_WATCH_STUCK_AFTER="0", LEAD_HEARTBEAT_AFTER="0")
        return subprocess.Popen([sys.executable, str(BIN / (script + ".py")), str(tmp)], env=env,
                                stdout=subprocess.PIPE, text=True)

    def lines(self, proc):
        """Let the loop poll its twenty times, however slow the machine, and return every line it printed."""
        out = proc.communicate(timeout=120)[0]
        self.assertEqual(proc.returncode, 0)
        return out.splitlines()

    def test_worker_mission_exits_at_once_silently(self):
        for script in ("worker-watch", "lead-heartbeat"):
            proc = self.launch(script, f"Goal: g\nMission: worker on {URL}\n", "idle")
            self.assertEqual(proc.wait(timeout=5), 0, script)
            self.assertEqual(proc.stdout.read(), "", script)

    def test_no_mission_prints_nothing_and_asks_no_herdr(self):
        for script in ("worker-watch", "lead-heartbeat"):
            proc = self.launch(script, None, "blocked")
            self.assertEqual(self.lines(proc), [], script)
            self.assertFalse((self.tmp / "herdr-called").exists(), script)

    def test_deleted_mission_ends_the_loop_silently(self):
        """Lead 5 deletes the mission; each monitor then exits, so `/exit` meets no background-work dialog."""
        for script in ("worker-watch", "lead-heartbeat"):
            proc = self.launch(script, MISSION, "working", ticks="100000")
            deadline = time.time() + 60
            while not (self.tmp / "herdr-called").exists() and time.time() < deadline:
                time.sleep(0.05)
            (self.tmp / "mission" / "s1.md").unlink()
            try:
                self.assertEqual(proc.wait(timeout=5), 0, script)
            finally:
                proc.kill()
            self.assertEqual(proc.stdout.read(), "", script)

    def test_heartbeat_holds_a_working_worker_through_unknown(self):
        proc = self.launch("lead-heartbeat", MISSION, "working", then="unknown")
        self.assertEqual(self.lines(proc), [])

    def test_working_prints_nothing(self):
        for script in ("worker-watch", "lead-heartbeat"):
            self.assertEqual(self.lines(self.launch(script, MISSION, "working")), [], script)

    def test_blocked_line_once(self):
        self.assertEqual(self.lines(self.launch("worker-watch", MISSION, "blocked")), [f"blocked a-7 {URL}"])

    def test_gone_line_once(self):
        self.assertEqual(self.lines(self.launch("worker-watch", MISSION, None)), [f"gone a-7 {URL}"])

    def test_idle_then_one_stuck_line(self):
        self.assertEqual(self.lines(self.launch("worker-watch", MISSION, "idle")),
                         [f"idle a-7 {URL}", f"stuck a-7 {URL}"])

    def test_closed_issue_is_not_stuck(self):
        self.assertEqual(self.lines(self.launch("worker-watch", MISSION, "idle", "CLOSED")), [f"idle a-7 {URL}"])

    def test_heartbeat_once_with_zero_workers(self):
        self.assertEqual(self.lines(self.launch("lead-heartbeat", LEAD, None)), [f"lead-heartbeat: team idle 0m, mission {PARENT}"])

    def test_heartbeat_once_with_a_blocked_worker(self):
        self.assertEqual(self.lines(self.launch("lead-heartbeat", MISSION, "blocked")),
                         [f"lead-heartbeat: team idle 0m, mission {PARENT}"])


if __name__ == "__main__":
    unittest.main()

"""`worker-start.py` run against a fake herdr, git and gh that log every call and play a Claude session behind a trust dialog.

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
PANE = "w1:p1"
ISSUE = "https://github.com/o/r/issues/7"
LEAD = "GOAL: g\nMISSION: leader of https://github.com/o/r/issues/1\n"

# One fake for all three tools, chosen by the name it is called as; state lives in files under $FAKE.
FAKE = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
d, tool, a = pathlib.Path(os.environ["FAKE"]), pathlib.Path(sys.argv[0]).name, sys.argv[1:]
with open(d / "calls", "a") as f:
    f.write(json.dumps([tool] + a) + "\n")
blocked = (d / "trust").exists() and not (d / "answered").exists()
if tool == "gh":
    print("main")
elif tool == "git":
    if a[2:4] == ["worktree", "add"]:
        pathlib.Path(a[5]).mkdir(parents=True)
    elif a[2:4] == ["config", "core.hooksPath"]:
        sys.exit(1)
    elif a[2] == "rev-parse":
        print(d / a[-1].split("/")[-1])
elif a[:2] == ["tab", "create"]:
    print(json.dumps({"result": {"root_pane": {"pane_id": "%s"}}}))
elif a[:2] == ["agent", "start"]:
    busy = d / "busy"
    n = int(busy.read_text()) if busy.exists() else 0
    if n:
        busy.write_text(str(n - 1))
        print(json.dumps({"error": {"code": "agent_pane_busy", "message": "not an available shell"}}))
        sys.exit(1)
    print(json.dumps({"error": {"code": "agent_not_ready"}} if blocked else {"result": {}}))
elif a[:2] == ["agent", "read"]:
    print("Quick safety check\n ❯ No, exit\n   Yes, I trust this folder" if blocked else "❯")
elif a[:2] == ["agent", "send-keys"] and a[3:] == ["down", "enter"] and blocked:
    (d / "answered").touch()
elif a[:2] == ["agent", "prompt"]:
    (d / "prompted").touch()
elif a[:2] == ["agent", "list"]:
    status = "blocked" if blocked else "working" if (d / "prompted").exists() else "idle"
    print(json.dumps({"result": {"agents": [{"name": "start-7", "agent_status": status, "interactive_ready": not blocked}]}}))
''' % PANE


class WorkerStart(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        for tool in ("herdr", "git", "gh"):
            (self.tmp / tool).write_text(FAKE)
            (self.tmp / tool).chmod(0o755)
        self.mission = self.tmp / "config" / "plugins" / "data" / "mumu-team-x" / "mission" / "s1.md"
        self.mission.parent.mkdir(parents=True)
        self.mission.write_text(LEAD)

    def start(self, *extra, trust=True, name="start-7", url=ISSUE, effort="low"):
        if trust:
            (self.tmp / "trust").touch()
        env = dict(os.environ, FAKE=str(self.tmp), PATH=f"{self.tmp}:{BIN}:{os.environ['PATH']}",
                   WORKER_START_TIMEOUT="3", WORKER_START_POLL="0.01",
                   CLAUDE_CONFIG_DIR=str(self.tmp / "config"), CLAUDE_CODE_SESSION_ID="s1")
        done = subprocess.run([sys.executable, str(BIN / "worker-start.py"), str(self.repo), name, effort, url, *extra],
                              env=env, capture_output=True, text=True, timeout=30)
        log = self.tmp / "calls"
        calls = [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []
        return done, calls

    def status(self):
        env = dict(os.environ, FAKE=str(self.tmp))
        out = subprocess.run([str(self.tmp / "herdr"), "agent", "list"], env=env, capture_output=True, text=True).stdout
        return json.loads(out)["result"]["agents"][0]["agent_status"]

    def test_trust_dialog_answered_yes_then_prompted_and_working(self):
        done, calls = self.start("--prompt", "/mumu-team:kickoff work u leader l")
        self.assertEqual(done.returncode, 0, done.stderr)
        tree = self.repo / ".claude" / "worktrees" / "start-7"
        self.assertEqual(done.stdout, f"start-7@{PANE} {tree}\n")
        keys = calls.index(["herdr", "agent", "send-keys", PANE, "down", "enter"])
        prompt = calls.index(["herdr", "agent", "prompt", PANE, "/mumu-team:kickoff work u leader l"])
        self.assertLess(keys, prompt, "prompted before the trust dialog was answered")
        self.assertEqual(self.status(), "working")
        self.assertIn(["git", "-C", str(self.repo), "worktree", "add", "--detach", str(tree), "origin/main"], calls)
        self.assertTrue((self.tmp / "hooks" / "pre-commit").exists() and (self.tmp / "hooks" / "pre-push").exists())

    def test_tab_marks_the_session_a_worker(self):
        """The marker the lead monitors exit on (`lib/team.py`)."""
        _, calls = self.start(trust=False)
        tab = next(c for c in calls if c[1:3] == ["tab", "create"])
        self.assertIn("--env", tab)
        self.assertEqual(tab[tab.index("--env") + 1], "MUMU_ROLE=worker")

    def test_worktrees_excluded_once(self):
        (self.tmp / "exclude").write_text("# kept")
        self.start(trust=False)
        self.start(trust=False)
        self.assertEqual((self.tmp / "exclude").read_text(), "# kept\n/.claude/worktrees/\n")

    def test_no_dialog_sends_no_keys(self):
        done, calls = self.start(trust=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertFalse([c for c in calls if c[1:3] == ["agent", "send-keys"]])
        self.assertFalse([c for c in calls if c[1:3] == ["agent", "prompt"]])

    def test_continue_reuses_the_worktree_and_resumes(self):
        (self.repo / ".claude" / "worktrees" / "start-7").mkdir(parents=True)
        done, calls = self.start("--continue", trust=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertFalse([c for c in calls if c[0] == "git" and "worktree" in c])
        start = next(c for c in calls if c[1:3] == ["agent", "start"])
        self.assertEqual(start[start.index("--") + 1:], ["--name", "start-7", "--agent", "mumu-team:worker", "--model", "opus", "--effort", "low", "--continue"])

    def test_session_never_ready_fails_naming_the_pane(self):
        (self.tmp / "herdr").write_text(FAKE.replace('and blocked:\n', 'and False:\n'))
        done, _ = self.start()
        self.assertEqual(done.returncode, 1)
        self.assertIn(f"herdr agent read {PANE}", done.stderr)

    def test_start_retried_while_pane_busy(self):
        (self.tmp / "busy").write_text("2")
        done, calls = self.start(trust=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len([c for c in calls if c[1:3] == ["agent", "start"]]), 3)

    def test_pane_always_busy_fails_naming_the_error(self):
        (self.tmp / "busy").write_text("100000")
        done, _ = self.start(trust=False)
        self.assertEqual(done.returncode, 1)
        self.assertIn("agent_pane_busy", done.stderr)

    def test_mission_gets_exactly_one_subscribe_line(self):
        """Started twice (a `gone` worker resumed), the lead's mission still names it once, after its own lines."""
        self.start(trust=False)
        self.start("--continue", trust=False)
        self.assertEqual(self.mission.read_text(), LEAD + f"SUBSCRIBE: start-7 {ISSUE}\n")

    def test_failed_start_writes_no_line(self):
        (self.tmp / "busy").write_text("100000")
        self.start(trust=False)
        self.assertEqual(self.mission.read_text(), LEAD)

    def test_no_mission_starts_nothing(self):
        self.mission.unlink()
        done, calls = self.start(trust=False)
        self.assertEqual(done.returncode, 1)
        self.assertIn("no mission", done.stderr)
        self.assertEqual(calls, [])

    def test_name_without_issue_number_refused_before_side_effects(self):
        url = "https://github.com/o/r/issues/73"
        done, calls = self.start(trust=False, name="rebuild-writing-documents", url=url)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("<topic>-73", done.stderr)
        self.assertEqual(calls, [], "worktree or tab touched")
        self.assertFalse((self.repo / ".claude" / "worktrees").exists())
        self.assertEqual(self.mission.read_text(), LEAD)

    def test_name_ending_in_the_issue_number_passes(self):
        url = "https://github.com/o/r/issues/73"
        (self.tmp / "herdr").write_text(FAKE.replace('"name": "start-7"', '"name": "writing-documents-73"'))
        done, _ = self.start(trust=False, name="writing-documents-73", url=url)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("SUBSCRIBE: writing-documents-73", self.mission.read_text())

    def test_name_ending_in_another_issue_number_refused(self):
        done, calls = self.start(trust=False, name="writing-documents-74", url="https://github.com/o/r/issues/73")
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual(calls, [])

    def test_high_effort_refused_before_side_effects(self):
        done, calls = self.start(trust=False, effort="high")
        self.assertEqual(done.returncode, 2)
        self.assertIn("--owner-effort", done.stderr)
        self.assertEqual(len(done.stderr.strip().splitlines()), 1)
        self.assertEqual(calls, [], "worktree or tab touched")
        self.assertEqual(self.mission.read_text(), LEAD)

    def test_high_effort_with_owner_flag_starts_at_high(self):
        done, calls = self.start("--owner-effort", trust=False, effort="high")
        self.assertEqual(done.returncode, 0, done.stderr)
        start = next(c for c in calls if c[1:3] == ["agent", "start"])
        self.assertEqual(start[start.index("--effort") + 1], "high")

    def test_low_and_medium_start(self):
        for effort in ("low", "medium"):
            with self.subTest(effort=effort):
                done, calls = self.start(trust=False, effort=effort)
                self.assertEqual(done.returncode, 0, done.stderr)
                start = [c for c in calls if c[1:3] == ["agent", "start"]][-1]
                self.assertEqual(start[start.index("--effort") + 1], effort)


if __name__ == "__main__":
    unittest.main()

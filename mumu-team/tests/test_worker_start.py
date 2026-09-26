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

# One fake for all three tools, chosen by the name it is called as; state lives in files under $FAKE.
FAKE = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
d, tool, a = pathlib.Path(os.environ["FAKE"]), pathlib.Path(sys.argv[0]).name, sys.argv[1:]
with open(d / "calls", "a") as f:
    f.write(json.dumps([tool] + a) + "\n")
blocked = (d / "trust").exists() and not (d / "answered").exists()
if tool == "gh":
    print((d / "prs").read_text() if a[:2] == ["pr", "list"] and (d / "prs").exists() else "" if a[:2] == ["pr", "list"] else "main")
elif tool == "git":
    if a[2:4] == ["worktree", "add"]:
        pathlib.Path(a[5]).mkdir(parents=True)
    elif a[2:4] == ["config", "core.hooksPath"]:
        sys.exit(1)
    elif a[2] == "ls-remote":
        print((d / "heads").read_text() if (d / "heads").exists() else "")
    elif a[2] == "rev-parse":
        print(d / a[-1].split("/")[-1])
elif a[:2] == ["tab", "create"]:
    print(json.dumps({"result": {"root_pane": {"pane_id": "%s"}}}))
elif a[:2] == ["agent", "start"]:
    (d / "name").write_text(a[2])
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
    print(json.dumps({"result": {"agents": [{"name": (d / "name").read_text() if (d / "name").exists() else "", "agent_status": status, "interactive_ready": not blocked}]}}))
''' % PANE


class WorkerStart(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.repo = self.tmp / "repo"
        (self.repo / ".git").mkdir(parents=True)
        for tool in ("herdr", "git", "gh"):
            (self.tmp / tool).write_text(FAKE)
            (self.tmp / tool).chmod(0o755)

    def start(self, *extra, trust=True, topic="start", url=ISSUE, effort="low", checkout=None, cwd=None):
        if trust:
            (self.tmp / "trust").touch()
        env = dict(os.environ, FAKE=str(self.tmp), PATH=f"{self.tmp}:{BIN}:{os.environ['PATH']}",
                   WORKER_START_TIMEOUT="3", WORKER_START_POLL="0.01")
        done = subprocess.run([sys.executable, str(BIN / "worker-start.py"), checkout or str(self.repo), topic, effort, url, *extra],
                              env=env, cwd=cwd, capture_output=True, text=True, timeout=30)
        log = self.tmp / "calls"
        calls = [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []
        return done, calls

    def test_relative_checkout_opens_the_tab_at_the_absolute_worktree(self):
        done, calls = self.start(checkout="repo", cwd=self.tmp)
        self.assertEqual(done.returncode, 0, done.stderr)
        tree = str(self.repo.resolve() / ".claude" / "worktrees" / "start-7-1")
        self.assertEqual([c[4] for c in calls if c[1:3] == ["tab", "create"]], [tree])

    def test_non_root_checkout_fails_naming_it_and_opens_no_tab(self):
        (self.repo / "sub").mkdir()
        (self.tmp / "plain").mkdir()
        for path in (str(self.repo / "sub"), str(self.tmp / "plain")):
            done, calls = self.start(checkout=path)
            self.assertEqual(done.returncode, 1, path)
            self.assertIn(path, done.stderr)
            self.assertFalse([c for c in calls if c[1:3] == ["tab", "create"]], path)

    def status(self):
        env = dict(os.environ, FAKE=str(self.tmp))
        out = subprocess.run([str(self.tmp / "herdr"), "agent", "list"], env=env, capture_output=True, text=True).stdout
        return json.loads(out)["result"]["agents"][0]["agent_status"]

    def test_trust_dialog_answered_yes_then_prompted_and_working(self):
        done, calls = self.start("--leader", "l")
        self.assertEqual(done.returncode, 0, done.stderr)
        tree = self.repo / ".claude" / "worktrees" / "start-7-1"
        self.assertEqual(done.stdout, f"start-7-1@{PANE} {tree}\n")
        keys = calls.index(["herdr", "agent", "send-keys", PANE, "down", "enter"])
        prompt = calls.index(["herdr", "agent", "prompt", PANE, f"/mumu-team:kickoff work {ISSUE} leader l"])
        self.assertLess(keys, prompt, "prompted before the trust dialog was answered")
        self.assertEqual(self.status(), "working")
        self.assertIn(["git", "-C", str(self.repo), "worktree", "add", "--detach", str(tree), "origin/main"], calls)
        self.assertTrue((self.tmp / "hooks" / "pre-commit").exists() and (self.tmp / "hooks" / "pre-push").exists())

    def test_tab_marks_the_session_a_worker(self):
        """The marker the lead monitors exit on (`scripts/team-watch.py`)."""
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
        (self.repo / ".claude" / "worktrees" / "start-7-1").mkdir(parents=True)
        done, calls = self.start("--continue", trust=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertFalse([c for c in calls if c[0] == "git" and "worktree" in c])
        start = next(c for c in calls if c[1:3] == ["agent", "start"])
        self.assertEqual(start[start.index("--") + 1:], ["--name", "start-7-1", "--agent", "mumu-team:worker", "--model", "opus", "--effort", "low", "--continue"])

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

    def test_attempt_is_one_more_than_the_largest_found(self):
        """Issue 12 with remote branches `a-12-1` and `b-12-2` gets k=3; other issues' names never count; none found gives k=1."""
        url = "https://github.com/o/r/issues/12"
        done, _ = self.start(trust=False, topic="fix-login", url=url)
        self.assertTrue(done.stdout.startswith("fix-login-12-1@"), done.stdout + done.stderr)
        (self.tmp / "heads").write_text("s1\trefs/heads/a-12-1\ns2\trefs/heads/b-12-2\ns3\trefs/heads/c-112-9\ns4\trefs/heads/d-12\n")
        done, _ = self.start(trust=False, topic="fix-login", url=url)
        self.assertTrue(done.stdout.startswith("fix-login-12-3@"), done.stdout + done.stderr)
        (self.tmp / "prs").write_text("e-12-4\nf-13-8\n")
        done, _ = self.start(trust=False, topic="fix-login", url=url)
        self.assertTrue(done.stdout.startswith("fix-login-12-5@"), done.stdout + done.stderr)

    def test_local_worktree_counts_as_an_attempt(self):
        (self.repo / ".claude" / "worktrees" / "start-7-1").mkdir(parents=True)
        done, _ = self.start(trust=False)
        self.assertTrue(done.stdout.startswith("start-7-2@"), done.stdout + done.stderr)

    def test_continue_without_a_worktree_fails_before_the_tab(self):
        done, calls = self.start("--continue", trust=False)
        self.assertEqual(done.returncode, 1)
        self.assertIn("--continue", done.stderr)
        self.assertFalse([c for c in calls if c[0] == "herdr"])

    def test_topic_not_lowercase_words_refused_before_side_effects(self):
        for topic in ("Fix_Login", "fix--login", ""):
            with self.subTest(topic=topic):
                done, calls = self.start(trust=False, topic=topic)
                self.assertEqual(done.returncode, 2)
                self.assertEqual(calls, [], "worktree or tab touched")
        self.assertFalse((self.repo / ".claude" / "worktrees").exists())

    def test_high_effort_refused_before_side_effects(self):
        done, calls = self.start(trust=False, effort="high")
        self.assertEqual(done.returncode, 2)
        self.assertIn("--owner-effort", done.stderr)
        self.assertEqual(len(done.stderr.strip().splitlines()), 1)
        self.assertEqual(calls, [], "worktree or tab touched")

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

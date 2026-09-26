"""`lead-start.py` run against the fake herdr, git and gh of `test_worker_start`, whose `gh` names the repository `main`.

Run: python3 -m unittest discover mumu-team/tests
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_worker_start import BIN, FAKE, PANE  # noqa: E402

GOAL = "https://github.com/o/main/issues/9"


class LeadStart(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.repo = self.tmp / "repo"
        (self.repo / ".git").mkdir(parents=True)
        for tool in ("herdr", "git", "gh"):
            (self.tmp / tool).write_text(FAKE)
            (self.tmp / tool).chmod(0o755)

    def start(self, *extra, checkout=None, cwd=None):
        (self.tmp / "trust").touch()
        env = dict(os.environ, FAKE=str(self.tmp), PATH=f"{self.tmp}:{os.environ['PATH']}",
                   LEAD_START_TIMEOUT="3", LEAD_START_POLL="0.01")
        done = subprocess.run([sys.executable, str(BIN / "lead-start.py"), checkout or str(self.repo), *extra],
                              env=env, cwd=cwd, capture_output=True, text=True, timeout=30)
        log = self.tmp / "calls"
        return done, [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []

    def claude_argv(self, calls):
        start = next(c for c in calls if c[1:3] == ["agent", "start"])
        return start[3], start[start.index("--") + 1:]

    def test_goal_starts_the_lead_agent_and_prompts_see(self):
        done, calls = self.start(GOAL)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, f"main-lead@{PANE}\n")
        self.assertEqual(self.claude_argv(calls), ("main-lead", ["--name", "main-lead", "--agent", "mumu-team:lead", "--model", "opus", "--effort", "medium"]))
        self.assertIn(["herdr", "tab", "create", "--cwd", str(self.repo), "--label", "main-lead"], calls)
        keys = calls.index(["herdr", "agent", "send-keys", PANE, "down", "enter"])
        prompt = calls.index(["herdr", "agent", "prompt", PANE, f"/mumu-team:kickoff see {GOAL}"])
        self.assertLess(keys, prompt, "prompted before the trust dialog was answered")

    def test_repo_name_is_made_a_herdr_name(self):
        (self.tmp / "gh").write_text("#!/bin/sh\necho Kalaluthien.GitHub.io.and-a-long-tail\n")
        done, calls = self.start(GOAL)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.claude_argv(calls)[0], "kalaluthien-github-io-lead")

    def test_no_goal_prompts_resume(self):
        done, calls = self.start()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(["herdr", "agent", "prompt", PANE, "/mumu-team:kickoff"], calls)

    def test_succeed_names_the_successor_next_and_keeps_given_flags(self):
        (self.tmp / "name").write_text("main-lead")
        done, calls = self.start("--succeed", "w9:p9", "--", "--model", "opus", "--effort", "high")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.claude_argv(calls), ("main-lead-next", ["--name", "main-lead", "--agent", "mumu-team:lead", "--model", "opus", "--effort", "high"]))
        self.assertIn(["herdr", "agent", "prompt", PANE, "/mumu-team:kickoff succeed w9:p9"], calls)

    def test_live_lead_refuses_a_second(self):
        (self.tmp / "name").write_text("main-lead")
        done, calls = self.start(GOAL)
        self.assertEqual(done.returncode, 1)
        self.assertIn("already live", done.stderr)
        self.assertFalse([c for c in calls if c[1:3] in (["tab", "create"], ["agent", "start"])])

    def test_relative_checkout_opens_the_tab_at_its_absolute_root(self):
        done, calls = self.start(GOAL, checkout="repo", cwd=self.tmp)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(["herdr", "tab", "create", "--cwd", str(self.repo.resolve()), "--label", "main-lead"], calls)

    def test_non_root_checkout_fails_naming_it_and_opens_no_tab(self):
        (self.repo / "sub").mkdir()
        (self.tmp / "plain").mkdir()
        for path in (str(self.repo / "sub"), str(self.tmp / "plain")):
            done, calls = self.start(GOAL, checkout=path)
            self.assertEqual(done.returncode, 1, path)
            self.assertIn(path, done.stderr)
            self.assertFalse([c for c in calls if c[1:3] == ["tab", "create"]], path)

    def test_bad_arguments_start_nothing(self):
        for extra in (["--succeed"], ["--continue"], [GOAL, GOAL]):
            done, calls = self.start(*extra)
            self.assertEqual(done.returncode, 2, extra)
            self.assertFalse(calls, extra)


if __name__ == "__main__":
    unittest.main()

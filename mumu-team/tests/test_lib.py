"""`lib/`'s modules, `gh` and `herdr` run as fakes that log their calls.

Run: python3 -m unittest discover mumu-team/tests
"""
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import gh  # noqa: E402
import herdr  # noqa: E402
import names  # noqa: E402
from gh import run  # noqa: E402

class Run(unittest.TestCase):
    def test_stdout_with_stdin_and_cwd(self):
        self.assertEqual(run("cat", stdin="hi\n"), "hi\n")
        self.assertEqual(run("pwd", cwd="/").strip(), "/")

    def test_failure_raises_with_stderr_and_stdout(self):
        with self.assertRaises(RuntimeError) as e:
            run(sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)")
        self.assertIn("err out", str(e.exception))

    def test_missing_command_raises(self):
        self.assertRaises(RuntimeError, run, "no-such-command-156")


class Names(unittest.TestCase):
    def test_worker_round_trips_its_attempt(self):
        self.assertEqual(names.worker("fold-rest", 22, 3), "fold-rest-22-3")
        self.assertEqual(names.attempt("fold-rest-22-3"), 3)
        self.assertEqual(names.attempt("fold-rest-22-3", n=22), 3)
        self.assertEqual(names.attempt("fold-rest-22-3", "fold-rest", 22), 3)

    def test_attempt_refuses_other_names_tasks_and_topics(self):
        for name, topic, n in [("mumu-lead", None, None), ("Fold-22-1", None, None), ("fold-22", None, None),
                               ("fold-22-1", None, 2), ("fold-22-1", "rest", 22), (None, None, None)]:
            with self.subTest(name=name, topic=topic, n=n):
                self.assertIsNone(names.attempt(name, topic, n))

    def test_lead_is_cut_so_its_successor_fits_herdr(self):
        self.assertEqual(names.lead("mumu-claude-plugin"), "mumu-claude-plugin-lead")
        self.assertEqual(names.lead("My Repo.v2"), "my-repo-v2-lead")
        self.assertLessEqual(len(names.lead("x" * 40) + "-next"), 32)

    def test_checkout_is_a_root_holding_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertRaises(RuntimeError, names.checkout, tmp)
            (pathlib.Path(tmp) / ".git").mkdir()
            self.assertEqual(names.checkout(tmp), pathlib.Path(tmp).resolve())

    def test_workers_are_named_workers_under_the_checkouts_worktrees(self):
        root = names.worktrees("/w/plugins")
        listed = [
            {"name": "fold-rest-22-1", "cwd": str(root / "fold-rest-22-1"), "agent_status": "working"},
            {"name": "plugins-lead", "cwd": "/w/plugins", "agent_status": "idle"},
            {"name": "other-5-1", "cwd": "/w/other/.claude/worktrees/other-5-1"},
            {"name": "sib-6-1", "cwd": "/w/plugins-2/.claude/worktrees/sib-6-1"},
            {"name": "no-cwd-7-1"},
        ]
        self.assertEqual(names.workers(listed, "/w/plugins"), {"fold-rest-22-1": "working"})


GH = r'''#!/usr/bin/env python3
import json, os, sys
open(os.environ["FAKE_LOG"], "a").write(json.dumps(sys.argv[1:]) + "\n")
print(os.environ.get("FAKE_OUT", ""))
sys.exit(int(os.environ.get("FAKE_EXIT", 0)))
'''


class Gh(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "gh").write_text(GH)
        (self.tmp / "gh").chmod(0o755)
        self.log = self.tmp / "log"
        self.env = {"PATH": f"{self.tmp}:{os.environ['PATH']}", "FAKE_LOG": str(self.log)}

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_repo_reads_one_field(self):
        with mock.patch.dict(os.environ, {**self.env, "FAKE_OUT": "main"}):
            self.assertEqual(gh.repo("defaultBranchRef"), "main")
        self.assertEqual(self.calls(), [["repo", "view", "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name"]])

    def test_held_reads_urls_or_answers_none(self):
        with mock.patch.dict(os.environ, {**self.env, "FAKE_OUT": json.dumps([{"url": "u1"}])}):
            self.assertEqual(gh.held("."), ["u1"])
        for out, code in [("not json", "0"), ("[]", "1")]:
            with self.subTest(out=out), mock.patch.dict(os.environ, {**self.env, "FAKE_OUT": out, "FAKE_EXIT": code}):
                self.assertIsNone(gh.held("."))

    def test_failure_raises(self):
        with mock.patch.dict(os.environ, {**self.env, "FAKE_EXIT": "1"}):
            self.assertRaises(RuntimeError, gh.gh, "issue", "view", "u")


HERDR = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
d, a = pathlib.Path(os.environ["FAKE"]), sys.argv[1:]
open(d / "calls", "a").write(json.dumps(a) + "\n")
if (d / "fail").exists():
    print(json.dumps({"error": {"code": (d / "fail").read_text()}}))
    sys.exit(1)
if a[:2] == ["agent", "list"]:
    ready = (d / "answered").exists()
    print(json.dumps({"result": {"agents": [{"name": "w-1-1", "pane_id": "p1", "interactive_ready": ready}]}}))
elif a[:2] == ["agent", "start"] and (d / "busy").exists():
    (d / "busy").unlink()
    print(json.dumps({"error": {"code": "agent_pane_busy"}}))
    sys.exit(1)
elif a[:2] == ["agent", "read"]:
    print("Yes, I trust this folder")
elif a[:2] == ["agent", "send-keys"]:
    (d / "answered").touch()
elif a[:2] == ["tab", "create"]:
    print(json.dumps({"result": {"root_pane": {"pane_id": "p9"}}}))
'''


class Herdr(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "herdr").write_text(HERDR)
        (self.tmp / "herdr").chmod(0o755)
        patch = mock.patch.dict(os.environ, {"PATH": f"{self.tmp}:{os.environ['PATH']}", "FAKE": str(self.tmp)})
        patch.start()
        self.addCleanup(patch.stop)

    def calls(self):
        return [json.loads(line) for line in (self.tmp / "calls").read_text().splitlines()]

    def test_agent_by_name(self):
        self.assertEqual(herdr.agent("w-1-1")["pane_id"], "p1")
        self.assertIsNone(herdr.agent("gone-1-1"))

    def test_open_tab_returns_its_pane(self):
        self.assertEqual(herdr.open_tab("/w", "w-1-1", "--no-focus"), "p9")
        self.assertEqual(self.calls(), [["tab", "create", "--cwd", "/w", "--label", "w-1-1", "--no-focus"]])

    def test_launch_retries_a_busy_pane_and_answers_the_trust_dialog(self):
        (self.tmp / "busy").touch()
        herdr.launch("w-1-1", "p1", ["--model", "opus"], 10, 0)
        calls = self.calls()
        self.assertEqual(sum(c[:2] == ["agent", "start"] for c in calls), 2)
        self.assertIn(["agent", "send-keys", "p1", "down", "enter"], calls)

    def test_launch_raises_on_another_error(self):
        (self.tmp / "fail").write_text("agent_exists")
        with self.assertRaises(RuntimeError) as e:
            herdr.launch("w-1-1", "p1", [], 10, 0)
        self.assertIn("agent_exists", str(e.exception))

    def test_unreadable_output_raises(self):
        (self.tmp / "herdr").write_text("#!/bin/sh\necho nope\n")
        self.assertRaises(RuntimeError, herdr.listed, "agent")


if __name__ == "__main__":
    unittest.main()

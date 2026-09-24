"""The `Stop` hook of `hooks/hooks.json`, run as Claude Code runs it, against a fake gh that plays the worker's issue.

Run: python3 -m unittest discover mumu-team/tests
"""
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent

FAKE_GH = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
d = pathlib.Path(os.environ["FAKE"])
with open(d / "calls", "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
print((d / ("prs.json" if sys.argv[1:3] == ["pr", "list"] else "issue.json")).read_text())
'''


class WorkerStop(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "gh").write_text(FAKE_GH)
        (self.tmp / "gh").chmod(0o755)
        self.tree = self.tmp / "repo" / ".claude" / "worktrees" / "stop-guard-19"
        self.tree.mkdir(parents=True)

    def stop(self, agent_type="mumu-team:worker", state="OPEN", comments=(), cwd=None, prs=()):
        (self.tmp / "issue.json").write_text(json.dumps({"state": state, "comments": [{"body": b} for b in comments]}))
        (self.tmp / "prs.json").write_text(json.dumps(list(prs)))
        payload = {"hook_event_name": "Stop", "session_id": "s", "cwd": str(cwd or self.tree), "stop_hook_active": False}
        if agent_type:
            payload["agent_type"] = agent_type
        commands = [h["command"] for entry in json.loads((ROOT / "hooks" / "hooks.json").read_text())["hooks"].get("Stop", [])
                    for h in entry["hooks"]]
        env = dict(os.environ, FAKE=str(self.tmp), CLAUDE_PLUGIN_ROOT=str(ROOT), PATH=f"{self.tmp}:{os.environ['PATH']}")
        outs = [subprocess.run(c, shell=True, input=json.dumps(payload), env=env, capture_output=True, text=True, timeout=30)
                for c in commands]
        calls = (self.tmp / "calls").read_text().splitlines() if (self.tmp / "calls").exists() else []
        return outs, calls

    def refused(self, outs):
        return any(o.returncode == 2 or o.stdout.strip() and json.loads(o.stdout).get("decision") == "block" for o in outs)

    def test_worker_with_no_merge_and_no_blocked_is_refused_naming_the_way_out(self):
        outs, calls = self.stop(comments=["a plan", "not BLOCKED: here"])
        for comments in (["a plan", "not BLOCKED: here"], ["BLOCKED: which name?", "Answer: stop-guard"]):
            with self.subTest(comments=comments):
                self.assertTrue(self.refused(self.stop(comments=comments)[0]))
        self.assertTrue(self.refused(outs), outs)
        self.assertIn("BLOCKED:", "".join(o.stdout + o.stderr for o in outs))
        self.assertIn("19", json.loads(calls[0])[2])

    def test_worker_stops_while_blocked_is_the_last_comment_or_the_issue_is_closed(self):
        for kwargs in ({"comments": ["a plan", "BLOCKED: which name?"]}, {"comments": ["  BLOCKED: stuck on x"]}, {"state": "CLOSED"}):
            with self.subTest(**kwargs):
                outs, _ = self.stop(**kwargs)
                self.assertFalse(self.refused(outs), outs)
                self.assertTrue(outs and all(o.returncode == 0 for o in outs), outs)

    def test_worker_stops_on_every_record_in_any_case_with_or_without_the_colon(self):
        """Records are written `UPPERCASE:` and read case-insensitively, the colon optional, so old comments still count."""
        for last in ("BLOCKED: which name?", "blocked: which name?", "Blocked which name?",
                     "STOPPED: the owner dropped it", "Stopped: the owner dropped it",
                     "WAITING: #120 to merge `lib/tree.py`", "Waiting: for #121's answer", "waiting on #120"):
            with self.subTest(last=last):
                outs, _ = self.stop(comments=["a plan", last])
                self.assertFalse(self.refused(outs), outs)

    def test_worker_stops_once_a_pull_request_from_its_branch_merged(self):
        merged = {"number": 5, "state": "MERGED", "headRefName": "stop-guard-19"}
        outs, calls = self.stop(prs=[merged])
        self.assertFalse(self.refused(outs), outs)
        self.assertIn("stop-guard-19", json.loads(calls[-1]))

    def test_worker_is_refused_when_no_merged_pull_request_is_its_own(self):
        for prs in ([{"number": 5, "state": "OPEN", "headRefName": "stop-guard-19"}],
                    [{"number": 5, "state": "CLOSED", "headRefName": "stop-guard-19"}],
                    [{"number": 5, "state": "MERGED", "headRefName": "other-guard-19"}]):
            with self.subTest(prs=prs):
                self.assertTrue(self.refused(self.stop(prs=prs)[0]))

    def test_record_words_inside_a_comment_do_not_stop(self):
        for last in ("Progress: I was blocked: by a flaky fixture", "Not waiting on anyone", "Answer: stopped: no",
                     "Blockedness is low", "Waitingroom booked"):
            with self.subTest(last=last):
                self.assertTrue(self.refused(self.stop(comments=[last])[0]))

    def test_session_without_worker_agent_stops_and_reads_nothing(self):
        for agent_type in (None, "mumu-team:lead", "mumu-team:reviewer"):
            with self.subTest(agent_type=agent_type):
                outs, calls = self.stop(agent_type=agent_type)
                self.assertFalse(self.refused(outs), outs)
                self.assertEqual(calls, [])

    def test_worker_outside_an_issue_worktree_stops(self):
        outs, calls = self.stop(cwd=self.tmp)
        self.assertFalse(self.refused(outs), outs)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()

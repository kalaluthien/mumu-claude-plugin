"""The `Stop` hook of `hooks/hooks.json`, run as Claude Code runs it, against a fake gh that plays the task, its pull requests and the root goals, and a fake ps.

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
a = sys.argv[1:]
name = {("issue", "list"): "goals.json", ("issue", "view"): "issue.json", ("pr", "list"): "prs.json"}[tuple(a[:2])]
f = d / name
print(f.read_text() if f.exists() else "[]")
'''

CLAUDE = 100
OPEN_PR = {"url": "https://github.com/o/r/pull/5", "headRefName": "stop-guard-19-2", "headRefOid": "abc123",
           "comments": [], "reviews": []}
GOAL = "https://github.com/o/r/issues/7"


def note(body, at):
    return {"body": body, "createdAt": at}


class Hook(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "gh").write_text(FAKE_GH)
        (self.tmp / "gh").chmod(0o755)
        self.tree = self.tmp / "repo" / ".claude" / "worktrees" / "stop-guard-19-2"
        self.tree.mkdir(parents=True)

    def stop(self, agent_type="mumu-team:worker", state="OPEN", comments=(), cwd=None, prs=(), goals=(), watch=None):
        (self.tmp / "issue.json").write_text(json.dumps({"state": state, "comments": [{"body": b} for b in comments]}))
        (self.tmp / "prs.json").write_text(json.dumps(list(prs)))
        (self.tmp / "goals.json").write_text(json.dumps([{"url": u} for u in goals]))
        table = [(1, 0, "launchd"), (CLAUDE, 1, "claude"), (200, 1, "claude --name other")]
        if watch is not None:
            table += [(300, watch, "/bin/zsh -c '\"/p/bin\"/team-watch.py'"), (301, 300, "python3 /p/bin/team-watch.py")]
        (self.tmp / "table").write_text("".join(f"{p:>6} {pp:>6} {c}\n" for p, pp, c in table))
        (self.tmp / "ps").write_text(f"#!/bin/sh\ncat '{self.tmp / 'table'}'\n")
        (self.tmp / "ps").chmod(0o755)
        payload = {"hook_event_name": "Stop", "session_id": "s", "cwd": str(cwd or self.tree), "stop_hook_active": False}
        if agent_type:
            payload["agent_type"] = agent_type
        commands = [h["command"] for entry in json.loads((ROOT / "hooks" / "hooks.json").read_text())["hooks"].get("Stop", [])
                    for h in entry["hooks"]]
        env = dict(os.environ, FAKE=str(self.tmp), CLAUDE_PLUGIN_ROOT=str(ROOT), PATH=f"{self.tmp}:{os.environ['PATH']}",
                   CLAUDE_PID=str(CLAUDE))
        outs = [subprocess.run(c, shell=True, input=json.dumps(payload), env=env, capture_output=True, text=True, timeout=30)
                for c in commands]
        calls = (self.tmp / "calls").read_text().splitlines() if (self.tmp / "calls").exists() else []
        return outs, calls

    def refused(self, outs):
        return any(o.returncode == 2 or o.stdout.strip() and json.loads(o.stdout).get("decision") == "block" for o in outs)

    def reason(self, outs):
        return "".join(json.loads(o.stdout)["reason"] for o in outs if o.stdout.strip())


class WorkerStop(Hook):
    def test_open_task_whose_last_keyword_is_blocked_stops(self):
        for comments in (["a plan", "BLOCKED: which name?"], ["  BLOCKED: stuck on x"], ["blocked which name?"],
                         ["BLOCKED: which name?", "a plain reference to #12"]):
            with self.subTest(comments=comments):
                outs, calls = self.stop(comments=comments, prs=[OPEN_PR])
                self.assertFalse(self.refused(outs), outs)
                self.assertTrue(outs and all(o.returncode == 0 for o in outs), outs)
                self.assertEqual(json.loads(calls[0])[:3], ["issue", "view", "19"])

    def test_open_task_otherwise_is_refused(self):
        for comments in ((), ["a plan", "not BLOCKED: here"], ["BLOCKED: which name?", "DECIDED: stop-guard"],
                         ["Progress: I was blocked: by a flaky fixture"], ["Blockedness is low"],
                         ["Waiting: #120 to merge"], ["Stopped: dropped"]):
            with self.subTest(comments=comments):
                self.assertTrue(self.refused(self.stop(comments=comments, prs=[OPEN_PR])[0]))

    def test_closed_task_stops(self):
        for comments in ((), ["DECIDED: dropped"]):
            self.assertFalse(self.refused(self.stop(state="CLOSED", comments=comments)[0]))

    def test_reopened_task_with_a_merged_old_attempt_is_refused(self):
        """Issue 19 reopened: `stop-guard-19-1` merged long ago; the worker on `-19-2` still has work while it is open."""
        self.tree.rename(self.tree.with_name("stop-guard-19-1"))
        tree = self.tmp / "repo" / ".claude" / "worktrees" / "stop-guard-19-2"
        tree.mkdir()
        outs, calls = self.stop(cwd=tree, prs=[])
        self.assertTrue(self.refused(outs))
        self.assertIn(["pr", "list", "--head", "stop-guard-19-2"], [json.loads(c)[:4] for c in calls])

    def test_session_without_worker_or_lead_agent_stops_and_reads_nothing(self):
        for agent_type in (None, "mumu-team:reviewer", "general-purpose"):
            with self.subTest(agent_type=agent_type):
                outs, calls = self.stop(agent_type=agent_type)
                self.assertFalse(self.refused(outs), outs)
                self.assertEqual(calls, [])

    def test_worker_outside_a_task_worktree_stops(self):
        for cwd in (self.tmp, self.tmp / "repo" / ".claude" / "worktrees" / "stop-guard-19"):
            cwd.mkdir(exist_ok=True)
            outs, calls = self.stop(cwd=cwd)
            self.assertFalse(self.refused(outs), outs)
            self.assertEqual(calls, [])

    def test_worker_without_a_pull_request_is_told_to_open_one(self):
        outs, _ = self.stop(comments=["a plan"])
        self.assertIn("open it with `pr`", self.reason(outs))
        self.assertNotIn("open it with `pr`", self.reason(self.stop(comments=["a plan"], prs=[OPEN_PR])[0]))

    def test_worker_with_an_approved_unmerged_head_is_told_to_run_merge_py(self):
        pr = dict(OPEN_PR, comments=[note("APPROVED: abc123", "2026-09-24T01:00:00Z")])
        self.assertIn("merge.py https://github.com/o/r/pull/5", self.reason(self.stop(prs=[pr])[0]))
        self.assertIn("`BLOCKED: owner review of <pr-url>`", self.reason(self.stop(prs=[pr])[0]))
        stale = dict(OPEN_PR, comments=[note("APPROVED: 0ld5ha", "2026-09-24T01:00:00Z")])
        self.assertNotIn("merge.py", self.reason(self.stop(prs=[stale])[0]))

    def test_worker_whose_newest_review_record_is_findings_is_told_to_fix_and_resume(self):
        pr = dict(OPEN_PR, comments=[note("APPROVED: 0ld5ha", "2026-09-24T01:00:00Z"), note("a note", "2026-09-24T03:00:00Z")],
                  reviews=[{"body": "FINDINGS:\n- x", "submittedAt": "2026-09-24T02:00:00Z"}])
        outs, _ = self.stop(prs=[pr])
        self.assertIn("`FINDINGS:`", self.reason(outs))
        self.assertIn("see https://github.com/o/r/pull/5", self.reason(outs))
        answered = dict(pr, comments=pr["comments"] + [note("APPROVED: 0ld5ha", "2026-09-24T04:00:00Z")])
        self.assertNotIn("FINDINGS", self.reason(self.stop(prs=[answered])[0]))

    def test_open_pull_request_awaiting_a_verdict_names_the_bounded_wait(self):
        self.assertIn("bounded foreground", self.reason(self.stop(prs=[OPEN_PR])[0]))


class LeadStop(Hook):
    def lead(self, **kwargs):
        return self.stop(agent_type="mumu-team:lead", cwd=self.tmp / "repo", **kwargs)

    def test_open_root_goal_without_team_watch_is_refused_naming_the_command(self):
        for watch in (None, 200):  # none, or another session's
            with self.subTest(watch=watch):
                outs, calls = self.lead(goals=[GOAL], watch=watch)
                self.assertTrue(self.refused(outs))
                self.assertIn("team-watch.py", self.reason(outs))
                self.assertIn(GOAL, self.reason(outs))
                self.assertIn("no:parent-issue", json.loads(calls[0]))

    def test_lead_stops_otherwise(self):
        for kwargs in ({"goals": [GOAL], "watch": CLAUDE}, {"goals": []}, {"goals": [], "watch": CLAUDE}):
            with self.subTest(**kwargs):
                outs, _ = self.lead(**kwargs)
                self.assertFalse(self.refused(outs), outs)


if __name__ == "__main__":
    unittest.main()

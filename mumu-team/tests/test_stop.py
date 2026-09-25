"""The `Stop` hook of `hooks/hooks.json`, run as Claude Code runs it, against a fake gh that plays the issue, its pull requests and a lead's parents, and a fake ps.

Run: python3 -m unittest discover mumu-team/tests
"""
import json
import os
import pathlib
import subprocess
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent

FAKE_GH = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
d = pathlib.Path(os.environ["FAKE"])
with open(d / "calls", "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
a = sys.argv[1:]
if a[:2] == ["api", "graphql"]:
    n = next(x for x in a if x.startswith("n="))[2:]
    name = f"parent-{n}.json"
elif a[:2] == ["pr", "list"] and "-R" in a:
    name = f"merged-{a[a.index('--head') + 1]}.json"
else:
    name = "prs.json" if a[:2] == ["pr", "list"] else "issue.json"
f = d / name
print(f.read_text() if f.exists() else "[]")
'''

CLAUDE = 100


OPEN_PR = {"url": "https://github.com/o/r/pull/5", "state": "OPEN", "headRefName": "stop-guard-19", "headRefOid": "abc123",
           "comments": [], "reviews": []}
PARENT = "https://github.com/o/r/issues/7"
SUB = "https://github.com/o/r/issues/8"


def note(body, at):
    return {"body": body, "createdAt": at}


def parent(state="OPEN", subs=(("OPEN", "a plan"),)):
    """A parent's graphql answer: its state and `(state, last comment)` per sub-issue."""
    nodes = [{"url": f"https://github.com/o/r/issues/{8 + i}", "state": st, "comments": {"nodes": [{"body": last}] if last else []}}
             for i, (st, last) in enumerate(subs)]
    return {"data": {"repository": {"issue": {"state": state, "subIssues": {"nodes": nodes}}}}}


def row(pid, ppid, command):
    """A `ps -o pid=,ppid=,lstart=,command=` row started a minute from now, after any code change."""
    start = time.strftime("%a %b %d %H:%M:%S %Y", time.localtime(time.time() + 60))
    return f"{pid:>6} {ppid:>6} {start} {command}"


def monitors(*names):
    """Process-table rows of this session's monitors, a shell under Claude and python under the shell."""
    return [r for i, n in enumerate(names) for r in (row(300 + 2 * i, CLAUDE, f"/bin/zsh -c '/p/bin/{n}.py /d'"),
                                                      row(301 + 2 * i, 300 + 2 * i, f"python3 /p/bin/{n}.py /d"))]


class Hook(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "gh").write_text(FAKE_GH)
        (self.tmp / "gh").chmod(0o755)
        self.tree = self.tmp / "repo" / ".claude" / "worktrees" / "stop-guard-19"
        self.tree.mkdir(parents=True)
        self.data = self.tmp / "config" / "plugins" / "data" / "mumu-team-x"
        (self.data / "mission").mkdir(parents=True)

    def stop(self, agent_type="mumu-team:worker", state="OPEN", comments=(), cwd=None, prs=(), mission=None,
             running=("worker-watch", "lead-heartbeat"), parents=None, merged=()):
        (self.tmp / "issue.json").write_text(json.dumps({"state": state, "comments": [{"body": b} for b in comments]}))
        (self.tmp / "prs.json").write_text(json.dumps(list(prs)))
        for n, answer in (parents or {}).items():
            (self.tmp / f"parent-{n}.json").write_text(json.dumps(answer))
        for old in self.tmp.glob("merged-*.json"):
            old.unlink()
        for name in merged:
            (self.tmp / f"merged-{name}.json").write_text(json.dumps([{"number": 5}]))
        if mission is not None:
            (self.data / "mission" / "s.md").write_text(mission)
        table = [row(1, 0, "launchd"), row(CLAUDE, 1, "claude"), *monitors(*running)]
        (self.tmp / "table").write_text("\n".join(table) + "\n")
        (self.tmp / "ps").write_text(f"#!/bin/sh\ncat '{self.tmp / 'table'}'\n")
        (self.tmp / "ps").chmod(0o755)
        payload = {"hook_event_name": "Stop", "session_id": "s", "cwd": str(cwd or self.tree), "stop_hook_active": False}
        if agent_type:
            payload["agent_type"] = agent_type
        commands = [h["command"] for entry in json.loads((ROOT / "hooks" / "hooks.json").read_text())["hooks"].get("Stop", [])
                    for h in entry["hooks"]]
        env = dict(os.environ, FAKE=str(self.tmp), CLAUDE_PLUGIN_ROOT=str(ROOT), PATH=f"{self.tmp}:{os.environ['PATH']}",
                   CLAUDE_PLUGIN_DATA=str(self.data), CLAUDE_CONFIG_DIR=str(self.tmp / "config"), CLAUDE_PID=str(CLAUDE))
        outs = [subprocess.run(c, shell=True, input=json.dumps(payload), env=env, capture_output=True, text=True, timeout=30)
                for c in commands]
        calls = (self.tmp / "calls").read_text().splitlines() if (self.tmp / "calls").exists() else []
        return outs, calls

    def refused(self, outs):
        return any(o.returncode == 2 or o.stdout.strip() and json.loads(o.stdout).get("decision") == "block" for o in outs)

    def reason(self, outs):
        return "".join(json.loads(o.stdout)["reason"] for o in outs if o.stdout.strip())


class WorkerStop(Hook):
    def test_worker_with_no_merge_and_no_blocked_is_refused_naming_the_way_out(self):
        outs, calls = self.stop(comments=["a plan", "not BLOCKED: here"], prs=[OPEN_PR])
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

    def test_session_without_worker_or_lead_agent_stops_and_reads_nothing(self):
        for agent_type in (None, "mumu-team:reviewer", "general-purpose"):
            with self.subTest(agent_type=agent_type):
                outs, calls = self.stop(agent_type=agent_type)
                self.assertFalse(self.refused(outs), outs)
                self.assertEqual(calls, [])

    def test_worker_outside_an_issue_worktree_stops(self):
        outs, calls = self.stop(cwd=self.tmp)
        self.assertFalse(self.refused(outs), outs)
        self.assertEqual(calls, [])

    def test_worker_without_a_pull_request_is_told_to_open_one(self):
        outs, _ = self.stop(comments=["a plan"])
        self.assertTrue(self.refused(outs))
        self.assertIn("open it with `pr`", self.reason(outs))
        self.assertNotIn("open it with `pr`", self.reason(self.stop(comments=["a plan"], prs=[OPEN_PR])[0]))

    def test_worker_with_an_approved_unmerged_head_is_told_to_run_merge_py(self):
        pr = dict(OPEN_PR, comments=[note("APPROVED: abc123", "2026-09-24T01:00:00Z")])
        outs, _ = self.stop(prs=[pr])
        self.assertTrue(self.refused(outs))
        self.assertIn("merge.py https://github.com/o/r/pull/5", self.reason(outs))
        stale = dict(OPEN_PR, comments=[note("APPROVED: 0ld5ha", "2026-09-24T01:00:00Z")])
        self.assertNotIn("merge.py", self.reason(self.stop(prs=[stale])[0]))

    def test_worker_whose_newest_review_record_is_findings_is_told_to_fix_and_resume(self):
        pr = dict(OPEN_PR, comments=[note("APPROVED: 0ld5ha", "2026-09-24T01:00:00Z"), note("a note", "2026-09-24T03:00:00Z")],
                  reviews=[{"body": "FINDINGS:\n- x", "submittedAt": "2026-09-24T02:00:00Z"}])
        outs, _ = self.stop(prs=[pr])
        self.assertTrue(self.refused(outs))
        self.assertIn("`FINDINGS:`", self.reason(outs))
        self.assertIn("see https://github.com/o/r/pull/5", self.reason(outs))
        answered = dict(pr, comments=pr["comments"] + [note("APPROVED: 0ld5ha", "2026-09-24T04:00:00Z")])
        self.assertNotIn("FINDINGS", self.reason(self.stop(prs=[answered])[0]))

    def test_approved_head_names_the_record_for_a_pending_owner_sign_off(self):
        """#87: an approval the owner has not signed off is not a merge; the reason names the record that stops."""
        pr = dict(OPEN_PR, comments=[note("APPROVED: abc123", "2026-09-24T01:00:00Z")])
        self.assertIn("`BLOCKED: owner review of <pr-url>`", self.reason(self.stop(prs=[pr])[0]))
        self.assertFalse(self.refused(self.stop(prs=[pr], comments=["BLOCKED: owner review of https://github.com/o/r/pull/5"])[0]))

    def test_open_pull_request_awaiting_a_verdict_names_the_bounded_wait(self):
        """#87: while the worker's own reviewer or eval runs, the reason names a bounded foreground wait, not another stop."""
        self.assertIn("bounded foreground", self.reason(self.stop(prs=[OPEN_PR])[0]))


class LeadStop(Hook):
    MISSION = f"GOAL: g\nMISSION: leader of {PARENT}\n"

    def lead(self, **kwargs):
        kwargs.setdefault("mission", self.MISSION)
        kwargs.setdefault("parents", {"7": parent()})
        return self.stop(agent_type="mumu-team:lead", **kwargs)

    def test_lead_with_no_case_open_stops(self):
        outs, calls = self.lead()
        self.assertFalse(self.refused(outs), outs)
        self.assertTrue(any("graphql" in c for c in calls), calls)

    def test_lead_without_a_mission_stops_and_reads_nothing(self):
        outs, calls = self.stop(agent_type="mumu-team:lead")
        self.assertFalse(self.refused(outs), outs)
        self.assertEqual(calls, [])

    def test_lead_missing_a_monitor_is_told_to_rearm(self):
        for running in (("worker-watch",), ("lead-heartbeat",), ()):
            with self.subTest(running=running):
                outs, _ = self.lead(running=running)
                self.assertTrue(self.refused(outs))
                self.assertIn("ensure-monitors.py", self.reason(outs))

    def test_lead_with_a_blocked_last_comment_on_an_open_issue_is_told_to_answer(self):
        outs, _ = self.lead(parents={"7": parent(subs=[("OPEN", "BLOCKED: which name?")])})
        self.assertTrue(self.refused(outs))
        self.assertIn(f"{SUB} ends in `BLOCKED:`", self.reason(outs))
        for subs in ([("OPEN", "Answer: stop-guard")], [("CLOSED", "BLOCKED: which name?"), ("OPEN", "x")]):
            with self.subTest(subs=subs):
                self.assertFalse(self.refused(self.lead(parents={"7": parent(subs=subs)})[0]))

    def test_lead_still_subscribed_to_a_merged_worker_is_told_to_close_it(self):
        mission = self.MISSION + f"SUBSCRIBE: stop-guard-8 {SUB}\n"
        outs, calls = self.lead(mission=mission, merged=["stop-guard-8"])
        self.assertTrue(self.refused(outs))
        self.assertIn("worker-close.py stop-guard-8", self.reason(outs))
        self.assertIn("o/r", json.loads(calls[-1]))
        self.assertFalse(self.refused(self.lead(mission=mission)[0]))

    def test_lead_with_an_open_parent_whose_sub_issues_all_closed_is_told_to_resolve(self):
        outs, _ = self.lead(parents={"7": parent(subs=[("CLOSED", "x"), ("CLOSED", None)])})
        self.assertTrue(self.refused(outs))
        self.assertIn(f"{PARENT} is closed: go to Lead 5", self.reason(outs))
        for answer in (parent(subs=[("CLOSED", "x"), ("OPEN", "x")]), parent(state="CLOSED", subs=[("CLOSED", "x")])):
            with self.subTest(answer=answer):
                self.assertFalse(self.refused(self.lead(parents={"7": answer})[0]))


if __name__ == "__main__":
    unittest.main()

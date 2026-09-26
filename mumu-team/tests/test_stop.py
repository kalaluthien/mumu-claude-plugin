"""The `Stop` hook of `hooks/hooks.json`, run as Claude Code runs it, against a fake gh that plays the open parentless issues, and a fake ps.

Run: python3 -m unittest discover mumu-team/tests
"""
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent

# `issue list` answers the issues of `held.json` whose kind its arguments name, as `kind:<kind>`.
FAKE_GH = r'''#!/usr/bin/env python3
import json, os, pathlib, re, sys
d = pathlib.Path(os.environ["FAKE"])
with open(d / "calls", "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
a = sys.argv[1:]
f = d / "held.json"
kinds = set(re.findall(r"kind:(\w+)", " ".join(a)))
print(json.dumps([{"url": i["url"]} for i in json.loads(f.read_text() if f.exists() else "[]") if i["kind"] in kinds]))
'''

CLAUDE = 100
GOAL = "https://github.com/o/r/issues/7"
TASK = "https://github.com/o/r/issues/8"


class Hook(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "gh").write_text(FAKE_GH)
        (self.tmp / "gh").chmod(0o755)
        self.tree = self.tmp / "repo" / ".claude" / "worktrees" / "stop-guard-19-2"
        self.tree.mkdir(parents=True)

    def stop(self, agent_type="mumu-team:worker", cwd=None, goals=(), tasks=(), watch=None):
        (self.tmp / "held.json").write_text(json.dumps([{"url": u, "kind": "goal"} for u in goals]
                                                       + [{"url": u, "kind": "task"} for u in tasks]))
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


class OtherStop(Hook):
    def test_worker_with_an_open_task_and_no_pull_request_stops_and_reads_nothing(self):
        outs, calls = self.stop(goals=[GOAL], tasks=[TASK])
        self.assertFalse(self.refused(outs), outs)
        self.assertTrue(outs and all(o.returncode == 0 for o in outs), outs)
        self.assertEqual(calls, [])

    def test_session_without_lead_agent_stops_and_reads_nothing(self):
        for agent_type in (None, "mumu-team:reviewer", "general-purpose"):
            with self.subTest(agent_type=agent_type):
                outs, calls = self.stop(agent_type=agent_type, goals=[GOAL])
                self.assertFalse(self.refused(outs), outs)
                self.assertEqual(calls, [])


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
                self.assertIn("no:parent-issue", " ".join(json.loads(calls[0])))

    def test_open_root_task_alone_without_team_watch_is_refused(self):
        outs, _ = self.lead(tasks=[TASK])
        self.assertTrue(self.refused(outs))
        self.assertIn(TASK, self.reason(outs))
        self.assertFalse(self.refused(self.lead(tasks=[TASK], watch=CLAUDE)[0]))

    def test_lead_stops_otherwise(self):
        for kwargs in ({"goals": [GOAL], "watch": CLAUDE}, {}, {"watch": CLAUDE}):
            with self.subTest(**kwargs):
                outs, _ = self.lead(**kwargs)
                self.assertFalse(self.refused(outs), outs)


if __name__ == "__main__":
    unittest.main()

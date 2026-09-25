"""`inject-mission.py` run as the UserPromptSubmit hook runs it, against a mission file on disk.

Run: python3 -m unittest discover mumu-team/tests
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

# The session's name keys its mission (`team.mission_path`): run as no named Claude session.
os.environ["CLAUDE_PID"] = str(os.getpid())

BIN = pathlib.Path(__file__).resolve().parent.parent / "bin"
URL = "https://github.com/o/r/issues/1"
LEAD = f"GOAL: g\nMISSION: leader of {URL}\nEXPECT: e; lead rules\n\nSUBSCRIBE: topic-2 https://github.com/o/r/issues/2\n"
WORKER = f"goal: g\nmission: worker on {URL}\nExpect: e\n"


class InjectMission(unittest.TestCase):
    def inject(self, text, event="UserPromptSubmit"):
        data = pathlib.Path(tempfile.mkdtemp())
        if text is not None:
            (data / "mission").mkdir()
            (data / "mission" / "s1.md").write_text(text)
        done = subprocess.run([sys.executable, str(BIN / "inject-mission.py")],
                              input=json.dumps({"hook_event_name": event, "session_id": "s1"}),
                              env=dict(os.environ, CLAUDE_PLUGIN_DATA=str(data)), capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"] if done.stdout else None

    def test_well_formed_missions_carry_no_warning(self):
        for text in (LEAD, WORKER):
            context = self.inject(text)
            self.assertIn(text, context)
            self.assertNotIn("not recognised", context)

    def test_each_unrecognised_line_is_named_with_the_expected_forms(self):
        bad = [f"MISSION: lead of {URL}", f"MISSION: leader {URL}", "SUBSCRIBE: topic-3", "NOTE: hello", "wrapped text"]
        for event in ("UserPromptSubmit", "SubagentStart"):
            context = self.inject(LEAD + "\n".join(bad) + "\n", event)
            for line in bad:
                self.assertIn(f"`{line}`", context)
            for form in ("MISSION: leader of <parent-url>", "MISSION: worker on <issue-url>", "SUBSCRIBE: <name> <issue-url>"):
                self.assertIn(form, context)

    def test_no_mission_no_output(self):
        self.assertIsNone(self.inject(None))


FAKE = r'''#!/usr/bin/env python3
import json, os, sys
with open(os.environ["CALLS"], "a") as f:
    f.write(json.dumps([os.path.basename(sys.argv[0])] + sys.argv[1:]) + "\n")
a = sys.argv[1:]
if a[:2] == ["repo", "view"]:
    print("o/r")
elif a[:2] == ["api", "graphql"]:
    sub = lambda n, state: {"number": n, "url": f"https://github.com/o/r/issues/{n}", "state": state}
    print(json.dumps({"data": {"repository": {"issues": {"nodes": [
        {"title": "Goal one", "url": "https://github.com/o/r/issues/1",
         "subIssues": {"nodes": [sub(2, "OPEN"), sub(3, "CLOSED"), sub(4, "OPEN")]}},
        {"title": "A plain issue", "url": "https://github.com/o/r/issues/9", "subIssues": {"nodes": []}}]}}}}))
elif a[:1] == ["ls-remote"]:
    print("aaa\trefs/heads/main\nbbb\trefs/heads/fix-thing-2\nccc\trefs/heads/old-3")
'''
REBUILT = ("GOAL: Goal one\nMISSION: leader of https://github.com/o/r/issues/1\n"
           "EXPECT: the ## Decisions of https://github.com/o/r/issues/1\n\n"
           "SUBSCRIBE: fix-thing-2 https://github.com/o/r/issues/2\n")


class NameKeyedCache(unittest.TestCase):
    """The mission is keyed by the session's `--name`, so a new session id finds it, and a lead's missing one is rebuilt from GitHub."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        for tool in ("gh", "git"):
            (self.tmp / tool).write_text(FAKE)
            (self.tmp / tool).chmod(0o755)
        self.calls = self.tmp / "calls"
        self.data = self.tmp / "data"

    def claude(self, name):
        """A stand-in Claude process started with `--name <name>`, as `team.session_name` reads it from ps."""
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "--name", name])
        self.addCleanup(proc.kill)
        return str(proc.pid)

    def inject(self, session, pid):
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(self.data), CLAUDE_PID=pid, CALLS=str(self.calls),
                   PATH=f"{self.tmp}:{os.environ['PATH']}")
        done = subprocess.run([sys.executable, str(BIN / "inject-mission.py")], env=env, capture_output=True, text=True,
                              input=json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": session, "cwd": str(self.tmp)}))
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"] if done.stdout else None

    def gh_calls(self):
        return sum(json.loads(line)[0] == "gh" for line in self.calls.read_text().splitlines()) if self.calls.exists() else 0

    def test_a_new_session_id_reads_the_mission_its_name_wrote(self):
        (self.data / "mission").mkdir(parents=True)
        (self.data / "mission" / "r-lead.md").write_text(LEAD)
        self.assertIn(LEAD, self.inject("new-id", self.claude("r-lead")))
        self.assertEqual(self.gh_calls(), 0)

    def test_a_missing_lead_mission_is_rebuilt_from_github_then_read_with_no_gh(self):
        pid = self.claude("r-lead")
        self.assertIn(REBUILT, self.inject("s1", pid))
        self.assertEqual((self.data / "mission" / "r-lead.md").read_text(), REBUILT)
        before = self.gh_calls()
        self.assertGreater(before, 0)
        for session in ("s1", "s2"):
            self.assertIn(REBUILT, self.inject(session, pid))
        self.assertEqual(self.gh_calls(), before)

    def test_a_named_session_whose_mission_is_under_its_id_still_reads_it(self):
        (self.data / "mission").mkdir(parents=True)
        (self.data / "mission" / "s1.md").write_text(WORKER)
        self.assertIn(WORKER, self.inject("s1", self.claude("topic-2")))
        (self.data / "mission" / "s1.md").write_text(LEAD)
        self.assertIn(LEAD, self.inject("s1", self.claude("r-lead")))
        self.assertEqual(self.gh_calls(), 0)
        self.assertFalse((self.data / "mission" / "r-lead.md").exists())

    def test_a_session_not_named_as_a_lead_runs_no_gh(self):
        self.assertIsNone(self.inject("s1", self.claude("topic-2")))
        self.assertIsNone(self.inject("s1", str(os.getpid())))
        self.assertEqual(self.gh_calls(), 0)


if __name__ == "__main__":
    unittest.main()

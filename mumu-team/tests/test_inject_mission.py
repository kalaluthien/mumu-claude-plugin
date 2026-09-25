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

# The session's name keys its mission (`team.session_key`): run as no named Claude session.
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


if __name__ == "__main__":
    unittest.main()

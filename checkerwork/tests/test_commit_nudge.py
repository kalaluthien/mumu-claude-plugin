"""What `commit-nudge.py` answers after a Bash call: an ask for each fitting skill not loaded, once per session, else nothing.

Run: python3 -m unittest discover checkerwork/tests
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "commit-nudge.py"


def git(repo, *args):
    subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True)


class CommitNudge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = os.path.join(self.tmp.name, "repo")
        self.data = os.path.join(self.tmp.name, "data")
        os.makedirs(self.repo)
        git(self.repo, "init", "-q")
        git(self.repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init")
        self.transcript = os.path.join(self.tmp.name, "t.jsonl")
        pathlib.Path(self.transcript).write_text("")

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self, rel, text):
        path = pathlib.Path(self.repo, rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        git(self.repo, "add", "-A")
        git(self.repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", rel)

    def hook(self, command="git add -A && git commit -m x", session="s1", cwd=None):
        call = {"tool_input": {"command": command}, "cwd": cwd or self.repo, "session_id": session,
                "transcript_path": self.transcript}
        p = subprocess.run([sys.executable, SCRIPT], input=json.dumps(call), capture_output=True, text=True,
                           env={**os.environ, "CLAUDE_PLUGIN_DATA": self.data})
        self.assertEqual(p.returncode, 0, p.stderr)
        return (json.loads(p.stdout) if p.stdout.strip() else None), p.stderr

    def test_asks_for_eval_after_a_skill_commit(self):
        self.commit("skills/tidy/SKILL.md", "---\nname: tidy\n---\n")
        out, _ = self.hook()
        self.assertEqual(out["decision"], "block")
        self.assertIn("checkerwork:contract", out["reason"])
        self.assertIn("eval (skills/tidy/SKILL.md)", out["reason"])
        self.assertNotIn("test (", out["reason"])

    def test_asks_for_test_after_a_code_commit(self):
        self.commit("scripts/guard.py", "x = 1\n")
        out, _ = self.hook()
        self.assertIn("test (scripts/guard.py)", out["reason"])

    def test_names_each_fitting_category_in_one_ask(self):
        self.commit("scripts/guard.py", "x = 1\n")
        self.commit("skills/tidy/SKILL.md", "x\n")
        git(self.repo, "reset", "-q", "--soft", "HEAD~2")
        git(self.repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "both")
        reason = self.hook()[0]["reason"]
        self.assertIn("test (scripts/guard.py); eval (skills/tidy/SKILL.md)", reason)

    def test_asks_once_per_session(self):
        self.commit("skills/tidy/SKILL.md", "x\n")
        self.assertIsNotNone(self.hook()[0])
        self.assertIsNone(self.hook()[0])
        self.assertIsNotNone(self.hook(session="s2")[0])

    def test_silent_when_the_skill_was_loaded(self):
        self.commit("skills/tidy/SKILL.md", "x\n")
        pathlib.Path(self.transcript).write_text(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "checkerwork:contract"}}]}}) + "\n")
        self.assertIsNone(self.hook()[0])

    def test_silent_for_a_change_no_skill_fits(self):
        self.commit("README.md", "A readme.\n")
        self.assertIsNone(self.hook()[0])

    def test_silent_for_a_call_that_is_not_a_commit(self):
        self.commit("skills/tidy/SKILL.md", "x\n")
        self.assertIsNone(self.hook(command="git status && git log -1")[0])

    def test_reads_the_repo_git_c_names(self):
        self.commit("agents/worker.md", "x\n")
        out, _ = self.hook(command="git -C repo commit -m x", cwd=self.tmp.name)
        self.assertIn("eval (agents/worker.md)", out["reason"])

    def test_names_the_path_under_diff_noprefix(self):
        git(self.repo, "config", "diff.noprefix", "true")
        self.commit("skills/tidy/SKILL.md", "x\n")
        self.assertIn("(skills/tidy/SKILL.md)", self.hook()[0]["reason"])

    def test_a_crash_allows_and_names_itself(self):
        out, err = self.hook(cwd=os.path.join(self.tmp.name, "missing"))
        self.assertIsNone(out)
        self.assertIn("commit-nudge.py:", err)


if __name__ == "__main__":
    unittest.main()

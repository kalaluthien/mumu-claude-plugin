"""What `run-verify.py` answers: a red `spec/verify.sh` refuses a commit and a stop with changes, naming its failures.

Run: python3 -m unittest discover mumu-verification/tests
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "run-verify.py"


class RunVerify(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.TemporaryDirectory()
        self.addCleanup(self.repo.cleanup)
        subprocess.run(["git", "init", "-q", self.repo.name], check=True)

    def hook(self, gate=None, event="PreToolUse", command="git add -A && git commit -m x", **call):
        if gate is not None:
            path = pathlib.Path(self.repo.name, "spec", "verify.sh")
            path.parent.mkdir(exist_ok=True)
            path.write_text(f"#!/bin/sh\necho 'FAIL check NoSelf: no expect'\nexit {gate}\n")
            path.chmod(0o755)
        call = {"cwd": self.repo.name, "hook_event_name": event, "tool_input": {"command": command}, **call}
        p = subprocess.run([sys.executable, SCRIPT], input=json.dumps(call), capture_output=True, text=True)
        self.assertEqual((p.returncode, p.stderr), (0, ""))
        return json.loads(p.stdout) if p.stdout.strip() else None

    def test_refuses_a_commit_while_the_gate_is_red(self):
        out = self.hook(gate=1)["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("FAIL check NoSelf: no expect", out["permissionDecisionReason"])

    def test_allows_a_green_commit_another_call_and_a_repo_without_a_gate(self):
        self.assertIsNone(self.hook())
        self.assertIsNone(self.hook(gate=1, command="git status"))
        self.assertIsNone(self.hook(gate=0))

    def test_holds_a_stop_with_changes_once(self):
        self.assertIn("FAIL check NoSelf", self.hook(gate=1, event="Stop")["reason"])
        self.assertIsNone(self.hook(event="Stop", stop_hook_active=True))
        subprocess.run(["git", "-C", self.repo.name, "add", "-A"], check=True)
        subprocess.run(["git", "-C", self.repo.name, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"])
        self.assertIsNone(self.hook(event="Stop"))


if __name__ == "__main__":
    unittest.main()

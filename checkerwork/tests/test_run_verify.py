"""What `run-verify.py` answers: in a repo holding a `spec/` model and no gate script of its own, the plugin's red gate
refuses a commit and a stop with changes, naming its failures.

Run: python3 -m unittest discover checkerwork/tests
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "run-verify.py"
MODEL = "sig A { f: set A }\nassert NoSelf { no a: A | a in a.f }\nfact { no a: A | a in a.f }\ncheck NoSelf for 2 expect 0\n"
MODEL += "pred grow[a: A] { some a.f }\nrun grow for 2 expect 1\n"


class RunVerify(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.TemporaryDirectory()
        self.addCleanup(self.repo.cleanup)
        subprocess.run(["git", "init", "-q", self.repo.name], check=True)

    def hook(self, gate=None, event="PreToolUse", command="git add -A && git commit -m x", **call):
        """gate: None for no model, 1 for a check with no witness, 0 for one with its witness."""
        for path, text in {"spec/m.als": MODEL, "tests/test_m.py": "def refuses_NoSelf(): pass\ndef scenario_grow(): pass\n"}.items():
            if gate is not None and (path.startswith("spec") or gate == 0):
                pathlib.Path(self.repo.name, path).parent.mkdir(exist_ok=True)
                pathlib.Path(self.repo.name, path).write_text(text)
        call = {"cwd": self.repo.name, "hook_event_name": event, "tool_input": {"command": command}, **call}
        p = subprocess.run([sys.executable, SCRIPT], input=json.dumps(call), capture_output=True, text=True,
                           env={**os.environ, "VERIFY_TESTS": "true"})
        self.assertEqual((p.returncode, p.stderr), (0, ""))
        return json.loads(p.stdout) if p.stdout.strip() else None

    def test_refuses_a_commit_while_the_gate_is_red(self):
        out = self.hook(gate=1)["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("FAIL check NoSelf: no refuses_NoSelf test", out["permissionDecisionReason"])

    def test_allows_another_call_and_a_repo_without_a_model(self):
        self.assertIsNone(self.hook())
        self.assertIsNone(self.hook(gate=1, command="git status"))

    @unittest.skipUnless(shutil.which("alloy"), "alloy not on PATH")
    def test_allows_a_green_commit(self):
        self.assertIsNone(self.hook(gate=0))

    def test_holds_a_stop_with_changes_once(self):
        self.assertIn("FAIL check NoSelf", self.hook(gate=1, event="Stop")["reason"])
        self.assertIsNone(self.hook(event="Stop", stop_hook_active=True))
        subprocess.run(["git", "-C", self.repo.name, "add", "-A"], check=True)
        subprocess.run(["git", "-C", self.repo.name, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"])
        self.assertIsNone(self.hook(event="Stop"))


if __name__ == "__main__":
    unittest.main()

"""What `run-verify.py` answers: in a repo holding a `spec/` model and no gate script of its own, the plugin's red gate
refuses a commit and a stop with changes, naming its failures; a tree the gate passed, or a session's own `verify.sh`
passed, runs it no more, and a busy machine gate is answered at once with "run it yourself".

Run: python3 -m unittest discover checkerwork/tests
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
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
                           env={**os.environ, "VERIFY_TESTS": "true", "HOMEOPS_GATE": "/none"})  # no machine gate
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


class RunVerifySkips(unittest.TestCase):
    """A stub gate counts its runs; a stub `gate.sh status` stands for the homeops machine gate."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = os.path.join(self.tmp.name, "repo")
        self.runs = os.path.join(self.tmp.name, "runs")
        self.gate = self.stub("gate", f"echo run >> {self.runs}\nexit 0\n")
        pathlib.Path(self.repo, "spec").mkdir(parents=True)
        pathlib.Path(self.repo, "spec", "m.als").write_text(MODEL)
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        self.machine = None

    def stub(self, name, body):
        path = os.path.join(self.tmp.name, name)
        pathlib.Path(path).write_text("#!/bin/sh\n" + body)
        os.chmod(path, 0o755)
        return path

    def busy_gate(self, status):
        self.machine = self.stub("gate.sh", f'[ "$1" = status ] && echo "{status}"\n')

    def count(self):
        return len(pathlib.Path(self.runs).read_text().split()) if os.path.exists(self.runs) else 0

    def hook(self, event="PreToolUse", command="git commit -m x", **call):
        env = {**os.environ, "HOME": self.tmp.name, "VERIFY_GATE": self.gate}
        if self.machine:
            env["HOMEOPS_GATE"] = self.machine
        call = {"cwd": self.repo, "hook_event_name": event, "tool_input": {"command": command}, **call}
        t = time.monotonic()
        p = subprocess.run([sys.executable, SCRIPT], input=json.dumps(call), capture_output=True, text=True, env=env)
        self.took = time.monotonic() - t
        self.assertEqual((p.returncode, p.stderr), (0, ""))
        return json.loads(p.stdout) if p.stdout.strip() else None

    def test_a_passed_tree_runs_the_gate_once_and_a_change_runs_it_again(self):
        self.assertIsNone(self.hook())
        self.assertIsNone(self.hook())
        self.assertIsNone(self.hook(event="Stop"))
        self.assertEqual(self.count(), 1)
        pathlib.Path(self.repo, "new.txt").write_text("a")  # untracked content counts
        self.hook()
        self.assertEqual(self.count(), 2)
        pathlib.Path(self.repo, "new.txt").write_text("b")  # one byte
        self.hook(event="Stop")
        self.assertEqual(self.count(), 3)

    def test_a_busy_machine_gate_is_answered_at_once_and_an_absent_one_is_not_read(self):
        self.busy_gate("0/1 held: none; room no")
        out = self.hook()["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("verify.sh yourself", out["permissionDecisionReason"])
        self.assertLess(self.took, 5)
        self.assertEqual(self.count(), 0)
        self.busy_gate("1/1 held: pid 1 'x'; room yes")
        self.assertEqual(self.hook()["hookSpecificOutput"]["permissionDecision"], "deny")
        self.busy_gate("0/1 held: none; room yes")
        self.assertIsNone(self.hook())
        self.assertEqual(self.count(), 1)
        self.machine = None
        pathlib.Path(self.repo, "a.txt").write_text("a")
        self.assertIsNone(self.hook())
        self.assertEqual(self.count(), 2)

    def test_a_pass_the_session_ran_lets_the_commit_through(self):
        self.busy_gate("0/1 held: none; room no")
        self.assertIsNone(self.hook(event="PostToolUse", command="./checkerwork/skills/spec/scripts/verify.sh"))
        self.assertIsNone(self.hook())
        self.assertEqual(self.count(), 0)
        pathlib.Path(self.repo, "a.txt").write_text("a")
        self.assertEqual(self.hook()["hookSpecificOutput"]["permissionDecision"], "deny")
        self.hook(event="PostToolUse", command="git status")  # another call passes nothing
        self.assertEqual(self.hook()["hookSpecificOutput"]["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()

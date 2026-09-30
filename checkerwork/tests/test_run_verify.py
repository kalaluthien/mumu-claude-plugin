"""What `run-verify.py` answers: in a repo holding a `spec/` model and no gate script of its own, the plugin's red gate
refuses a commit, naming its failures; a tree the gate passed, or `verify.sh` passed by its own record, runs it no more,
a busy machine gate is answered at once with "run it yourself", and a stop is never gated.

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

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "run-verify.py"
VERIFY = ROOT / "skills" / "contract" / "scripts" / "verify.sh"
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
        self.assertIsNone(self.hook())
        self.assertEqual(self.count(), 1)
        pathlib.Path(self.repo, "new.txt").write_text("a")  # untracked content counts
        self.hook()
        self.assertEqual(self.count(), 2)
        pathlib.Path(self.repo, "new.txt").write_text("b")  # one byte
        self.hook()
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

    def test_a_stop_is_never_gated_and_no_stop_hook_is_registered(self):
        pathlib.Path(self.repo, "a.txt").write_text("a")  # a changed tree that never passed
        for machine in (None, "0/1 held: none; room no"):
            if machine:
                self.busy_gate(machine)
            self.assertIsNone(self.hook(event="Stop", tool_input={}))  # a Stop call carries no command
            self.assertEqual(self.count(), 0)
        hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text())["hooks"]
        self.assertNotIn("Stop", hooks)
        self.assertNotIn("run-verify", json.dumps(hooks.get("PostToolUse")))

    def verify(self, tests, how="background"):
        """Run the real verify.sh at the repo's root as a Bash call would; `tests` is the repo's test command."""
        pathlib.Path(self.repo, "spec", "m.als").write_text("sig A {}\n")  # no command, so no alloy
        env = {**os.environ, "VERIFY_TESTS": tests}
        if how == "background":
            return subprocess.Popen([str(VERIFY)], cwd=self.repo, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return subprocess.Popen(f"bash {VERIFY} 2>&1 | tail -20", shell=True, cwd=self.repo, env=env, stdout=subprocess.DEVNULL)

    def test_a_verify_run_that_exited_0_lets_the_next_commit_through(self):
        self.busy_gate("0/1 held: none; room no")  # the hook could not run the gate
        for how in ("background", "foreground"):
            with self.subTest(how):
                pathlib.Path(self.repo, f"{how}.txt").write_text(how)  # a new tree each time
                self.assertEqual(self.verify("true", how).wait(30), 0)
                self.assertIsNone(self.hook())
                self.assertEqual(self.count(), 0)

    def test_no_pass_is_recorded_before_the_exit_or_by_a_failure_or_a_changed_tree(self):
        started, go = os.path.join(self.tmp.name, "started"), os.path.join(self.tmp.name, "go")
        run = self.verify(f"touch {started}; while [ ! -e {go} ]; do sleep 0.05; done")
        for _ in range(200):
            if os.path.exists(started):
                break
            time.sleep(0.05)
        self.assertIsNone(run.poll())  # not exited yet
        self.assertIsNone(self.hook())  # the hook runs the gate
        self.assertEqual(self.count(), 1)
        pathlib.Path(go).write_text("")
        self.assertEqual(run.wait(30), 0)
        pathlib.Path(self.repo, "b.txt").write_text("b")
        for tests, code in (("false", 1), (f"echo x >> {self.repo}/changed.txt", 0)):
            before = self.count()
            self.assertEqual(self.verify(tests).wait(30), code)
            self.assertIsNone(self.hook())
            self.assertEqual(self.count(), before + 1, tests)


if __name__ == "__main__":
    unittest.main()

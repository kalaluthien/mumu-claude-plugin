"""run-evals.py and a pytest session over every test file queue at the machine gate through `gate.sh hold <own pid>`,
the gate found through $HOMEOPS_GATE or the subjects/gate/hook.sh registered in ~/.claude/settings.json.

Run: uvx pytest paperwork/tests/test_gate.py -q
"""
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUN_EVALS = ROOT / "scripts" / "run-evals.py"
MACHINE_GATE = ROOT / "lib" / "machine_gate.py"
CONFTEST = ROOT / "tests" / "conftest.py"

# `hold` logs its arguments, exits 75 STUB_75 times, then STUB_EXIT (default 0)
GATE = """#!/bin/sh
echo "$@" >> "$LOG"
[ "$1" = hold ] || exit 64
n=$(cat "$COUNT" 2>/dev/null || echo 0)
echo $((n + 1)) > "$COUNT"
[ "$n" -lt "${STUB_75:-0}" ] && exit 75
exit "${STUB_EXIT:-0}"
"""
CLAUDE = """#!/bin/sh
echo "work HELD=$HOMEOPS_GATE_HELD" >> "$LOG"
"""
TEST_FILE = """import os


def test_it():
    open(os.environ["LOG"], "a").write("work\\n")
"""


def script(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def dead_pid():
    p = subprocess.Popen(["true"])
    p.wait()
    return p.pid


class Gate(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.log = self.tmp / "log"
        self.gate = self.tmp / "homeops" / "subjects" / "gate"
        script(self.gate / "gate.sh", GATE)
        script(self.gate / "hook.sh", "#!/bin/sh\n")
        script(self.tmp / "bin" / "claude", CLAUDE)
        self.home = self.tmp / "home"
        (self.home / ".claude").mkdir(parents=True)

    def env(self, registered=False, gate=None, **extra):
        """An environment with no gate unless `gate` (HOMEOPS_GATE) or `registered` (settings.json under the stub HOME)."""
        env = {k: v for k, v in os.environ.items() if not k.startswith(("HOMEOPS_", "STUB_"))}
        env.update(HOME=str(self.home), LOG=str(self.log), COUNT=str(self.tmp / "count"),
                   PATH=f"{self.tmp / 'bin'}:{env['PATH']}", **{k: str(v) for k, v in extra.items()})
        command = f"[ -x '{self.gate}/hook.sh' ] && exec '{self.gate}/hook.sh'; exit 0"
        settings = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": command}]}]}}
        (self.home / ".claude" / "settings.json").write_text(json.dumps(settings if registered else {}))
        if gate:
            env["HOMEOPS_GATE"] = str(gate)
        return env

    def lines(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def evals(self, **kw):
        p = subprocess.Popen([sys.executable, str(RUN_EVALS)], env=self.env(**kw), cwd=self.tmp,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p.wait()
        return p.pid

    def session(self, files, **kw):
        """A pytest session over `files` of a copy of this folder's layout holding two test files and the conftest."""
        for src, dst in ((MACHINE_GATE, "lib/machine_gate.py"), (CONFTEST, "tests/conftest.py")):
            (self.tmp / "paperwork" / dst).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, self.tmp / "paperwork" / dst)
        for name in ("test_a.py", "test_b.py"):
            (self.tmp / "paperwork" / "tests" / name).write_text(TEST_FILE)
        tests = self.tmp / "paperwork" / "tests"
        args = [str(tests)] if files == "all" else [str(tests / "test_a.py")]
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *args], env=self.env(**kw),
                           cwd=self.tmp, capture_output=True, text=True)
        return p

    def held(self, prefix="hold "):
        return [x for x in self.lines() if x.startswith(prefix)]

    def test_d1_run_evals_holds_its_pid_before_the_eval_and_passes_it_on(self):
        pid = self.evals(gate=self.gate / "gate.sh")
        first, second = self.lines()
        self.assertEqual(first, f"hold {pid} paperwork run-evals")
        self.assertEqual(second, f"work HELD={pid}")

    def test_d2_full_session_holds_a_slot_before_its_first_test_and_one_file_takes_none(self):
        self.assertEqual(self.session("all", gate=self.gate / "gate.sh").returncode, 0)
        lines = self.lines()
        self.assertTrue(lines[0].startswith("hold "), lines)
        self.assertEqual(lines.count("work"), 2, lines)
        self.log.unlink()
        self.assertEqual(self.session("one", gate=self.gate / "gate.sh").returncode, 0)
        self.assertEqual(self.lines(), ["work"])

    def test_d3_gate_found_through_settings_registration_or_homeops_gate(self):
        pid = self.evals(registered=True)
        self.assertEqual(self.lines(), [f"hold {pid} paperwork run-evals", f"work HELD={pid}"])
        self.log.unlink()
        pid = self.evals(gate=self.gate / "gate.sh")
        self.assertEqual(self.lines()[0], f"hold {pid} paperwork run-evals")
        self.log.unlink()
        self.session("all", registered=True)
        self.assertEqual(len(self.held()), 1, self.lines())

    def test_d4_exit_75_is_asked_again_and_the_work_waits(self):
        self.evals(gate=self.gate / "gate.sh", STUB_75=2)
        lines = self.lines()
        self.assertEqual([x.split()[0] for x in lines], ["hold", "hold", "hold", "work"], lines)
        self.log.unlink()
        (self.tmp / "count").unlink()
        self.session("all", gate=self.gate / "gate.sh", STUB_75=2)
        lines = self.lines()
        self.assertEqual([x.split()[0] for x in lines], ["hold", "hold", "hold", "work", "work"], lines)

    def test_d5_nested_takes_none_other_paths_run_the_work(self):
        gate = self.gate / "gate.sh"
        # a live holder: no hold, the work runs with the holder passed on
        self.evals(gate=gate, HOMEOPS_GATE_HELD=os.getpid())
        self.assertEqual(self.lines(), [f"work HELD={os.getpid()}"])
        self.log.unlink()
        self.session("all", gate=gate, HOMEOPS_GATE_HELD=os.getpid())
        self.assertEqual(self.lines(), ["work", "work"])
        self.log.unlink()
        # a holder that is gone is no holder
        self.evals(gate=gate, HOMEOPS_GATE_HELD=dead_pid())
        self.assertEqual(len(self.held()), 1, self.lines())
        self.log.unlink()
        # no gate found: the work runs
        self.evals()
        self.assertEqual(self.lines(), ["work HELD="])
        self.log.unlink()
        self.assertEqual(self.session("all").returncode, 0)
        self.assertEqual(self.lines(), ["work", "work"])
        self.log.unlink()
        # a hold failing other than 75 does not stop the work
        self.evals(gate=gate, STUB_EXIT=1)
        self.assertEqual([x.split()[0] for x in self.lines()], ["hold", "work"])
        self.log.unlink()
        self.assertEqual(self.session("all", gate=gate, STUB_EXIT=1).returncode, 0)
        self.assertEqual(self.lines().count("work"), 2)


if __name__ == "__main__":
    unittest.main()

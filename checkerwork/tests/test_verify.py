"""What `verify.sh` answers for a repo: each missed expect, missing expect and unmatched witness named, then the suite.

Run: python3 -m unittest discover checkerwork/tests
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import receipt  # noqa: E402

VERIFY = pathlib.Path(__file__).resolve().parent.parent / "skills" / "contract" / "scripts" / "verify.sh"
BASE = "sig A { f: set A }\nassert NoSelf { no a: A | a in a.f }\nfact { no a: A | a in a.f }\nrun {} for 2 expect 1\n"
FLOW, SCENARIO = "pred grow[a: A] { some a.f }\nrun grow for 2 expect 1\n", "def scenario_grow(): pass\n"
MODEL, GOOD, REFUSES = BASE + FLOW, "check NoSelf for 2 expect 0\n", "def refuses_NoSelf(): pass\n"
WITNESS, NONE = REFUSES + SCENARIO, "FAIL check NoSelf: no refuses_NoSelf test\n"
SHRINK, GUARD = "pred shrink[a: A] { no a.f }\nrun shrink for 2 expect 1", "run Admits { some a: A | some a.f } for 2 expect 1\n"
CASES = {  # name: (check.als tail or None for no spec, {file: text}, suite command or None unset), (exit, stdout)
    "passes": ((GOOD, {"test_m.py": WITNESS}, "true"), (0, "")),
    "no model": ((None, {}, "true"), (0, "no model\n")),
    "parse": (("check NoSelf for 2 expect 0 }\n", {"test_m.py": WITNESS}, "true"), (1, "FAIL spec/m/check.als: did not parse\n")),
    "no expect": (("check NoSelf for 2\n", {"test_m.py": WITNESS}, "true"), (1, "FAIL check NoSelf: no expect\n")),
    "missed expect": (("check NoSelf for 2 expect 1\n", {"test_m.py": WITNESS}, "true"), (1, "FAIL check NoSelf: expect 1 missed\n")),
    "no witness": ((GOOD, {"tests/test_s.py": SCENARIO}, "true"), (1, NONE)),
    "stale witness": ((GOOD, {"test_m.py": WITNESS + "refuses_Gone\n"}, "true"), (1, "FAIL test refuses_Gone: names no check\n")),
    "witness in docs or build": ((GOOD, {"docs/test_a.py": WITNESS, "app/build/test_a.py": WITNESS, "tests/test_s.py": SCENARIO},
                                  "true"), (1, NONE)),
    "witness in no test file": ((GOOD, {"src/a.py": WITNESS, "tests/test_s.py": SCENARIO}, "true"), (1, NONE)),
    "witness in tests/": ((GOOD, {"tests/test_a.py": WITNESS}, "true"), (0, "")),
    "witness in androidTest/": ((GOOD, {"app/src/androidTest/k/A.kt": WITNESS}, "true"), (0, "")),
    "witness in *Test.kt": ((GOOD, {"src/k/ATest.kt": WITNESS}, "true"), (0, "")),
    "gaps counted": (("check NoSelf for 2 expect 0 -- gap #7\n", {"tests/test_a.py": "# gap #12\n" + WITNESS + "# gap #7\n"}, "true"),
                     (0, "GAP #7: 2 marks\nGAP #12: 1 marks\n")),
    "flow run paired": ((GOOD, {"tests/test_a.py": WITNESS}, "true"), (0, "")),
    "flow run unpaired": ((GOOD, {"tests/test_a.py": REFUSES}, "true"), (1, "FAIL run grow: no scenario_grow test\n")),
    "stale scenario": ((GOOD, {"tests/test_a.py": WITNESS + "scenario_gone\n"}, "true"),
                       (1, "FAIL test scenario_gone: names no flow run\n")),
    "flow run gap": ((GOOD + SHRINK + " -- gap #9\n", {"tests/test_a.py": WITNESS}, "true"), (0, "GAP #9: 1 marks\n")),
    "guard run unpaired": ((GOOD + GUARD, {"tests/test_a.py": WITNESS}, "true"), (0, "")),
    "module no flow run": ((None, {"spec/n/n.als": BASE + GOOD + GUARD, "tests/test_a.py": REFUSES}, "true"),
                           (1, "FAIL module spec/n: checks and no flow run\n")),
    "module one flow run": ((None, {"spec/n/n.als": BASE + GOOD + FLOW, "tests/test_a.py": WITNESS}, "true"), (0, "")),
    "module guard runs, gap": ((None, {"spec/n/n.als": BASE + GOOD + GUARD + "-- gap #4\n", "tests/test_a.py": REFUSES}, "true"),
                               (0, "GAP #4: 1 marks\n")),
    "map alone": ((GOOD, {"spec/map.als": "module map\nsig A {}\n", "tests/test_a.py": WITNESS}, "true"), (0, "")),
    "suite": ((GOOD, {"test_m.py": WITNESS}, "false"), (1, "FAIL tests: false\n")),
    "suite chained": ((GOOD, {"test_m.py": WITNESS}, "true && false"), (1, "FAIL tests: true && false\n")),
    "no model, suite":((None, {}, "false"), (1, "no model\nFAIL tests: false\n")),
    "suite unset": ((GOOD, {"tests/test_m.py": WITNESS + "print('ran')\n"}, None),
                    (1, "FAIL tests: set VERIFY_TESTS to the repo's test command in .claude/settings.json env\n")),
}


@unittest.skipUnless(shutil.which("alloy"), "alloy not on PATH")
class Verify(unittest.TestCase):
    def test_cases(self):
        for name, ((check, tests, suite), want) in CASES.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as repo:
                os.makedirs(f"{repo}/spec/m")
                if check is not None:
                    pathlib.Path(repo, "spec/m/check.als").write_text(MODEL + check)
                for path, text in tests.items():
                    pathlib.Path(repo, path).parent.mkdir(parents=True, exist_ok=True)
                    pathlib.Path(repo, path).write_text(text)
                env = {k: v for k, v in os.environ.items() if k != "VERIFY_TESTS"}
                p = subprocess.run([VERIFY], cwd=repo, capture_output=True, text=True,
                                   env=env if suite is None else {**env, "VERIFY_TESTS": suite})
                self.assertEqual((p.returncode, p.stdout), want)


BASE_A, MODEL_A = "sig A { f: set A }\nfact { no a: A | a in a.f }\n", "open base\npred grow[a: A] { some a.f }\n"
CHECK_A = "open model\nassert NoSelf { no a: A | a in a.f }\ncheck NoSelf for 2 expect %d\nrun grow for 2 expect 1\n"
N_A = ("open util/ordering[A]\nsig A {}\nassert Ok { no first.prev }\ncheck Ok for 2 expect 0\n"
       "pred step { some A }\nrun step for 2 expect 1\n")
TESTS = "def refuses_NoSelf(): pass\ndef refuses_Ok(): pass\ndef scenario_grow(): pass\ndef scenario_step(): pass\n"
FILES = {"spec/m/base.als": BASE_A, "spec/m/model.als": MODEL_A, "spec/m/check.als": CHECK_A % 0, "spec/n/n.als": N_A,
         "tests/test_a.py": TESTS}
SHIM = "#!/bin/bash\n[ \"$1\" = exec ] && echo \"${@: -1}\" >> \"$ALLOY_LOG\"\nexec \"$REAL_ALLOY\" \"$@\"\n"
CHECK, N = "spec/m/check.als", "spec/n/n.als"


@unittest.skipUnless(shutil.which("alloy"), "alloy not on PATH")
class Receipts(unittest.TestCase):
    """`alloy exec` calls per `verify.sh` run, counted by a logging shim first on PATH."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        tmp = pathlib.Path(self.tmp.name)
        (tmp / "bin").mkdir()
        (tmp / "bin/alloy").write_text(SHIM)
        (tmp / "bin/alloy").chmod(0o755)
        self.repo = tmp / "repo"
        self.env = {**os.environ, "PATH": f"{tmp / 'bin'}:{os.environ['PATH']}", "REAL_ALLOY": shutil.which("alloy"),
                    "ALLOY_LOG": str(tmp / "calls"), "VERIFY_TESTS": "true"}
        for name, text in FILES.items():
            self.write(name, text)
        for cmd in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "m"]):
            subprocess.run(["git", *cmd], cwd=self.repo, check=True, capture_output=True)

    def write(self, name, text, repo=None):
        path = (repo or self.repo) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def run_verify(self, repo=None):
        log = pathlib.Path(self.env["ALLOY_LOG"])
        log.write_text("")
        p = subprocess.run([VERIFY], cwd=repo or self.repo, capture_output=True, text=True, env=self.env)
        return p.returncode, p.stdout, log.read_text().split()

    def store(self):
        return pathlib.Path(subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=self.repo,
                                           capture_output=True, text=True).stdout.strip(), "spec-receipts")

    def test_first_run_runs_every_model(self):
        self.assertEqual(self.run_verify(), (0, "", [CHECK, N]))

    def test_unchanged_tree_runs_nothing(self):
        self.run_verify()
        self.assertEqual(self.run_verify(), (0, "", []))

    def test_changed_model_alone(self):
        self.run_verify()
        self.write(N, N_A + "-- edit\n")
        self.assertEqual(self.run_verify(), (0, "", [N]))

    def test_changed_opened_file(self):
        self.run_verify()
        self.write("spec/m/model.als", MODEL_A + "-- edit\n")
        self.assertEqual(self.run_verify(), (0, "", [CHECK]))

    def test_changed_file_two_opens_away(self):
        self.run_verify()
        self.write("spec/m/base.als", BASE_A + "-- edit\n")
        self.assertEqual(self.run_verify(), (0, "", [CHECK]))

    def test_second_worktree_shares_receipts(self):
        self.run_verify()
        other = pathlib.Path(self.tmp.name) / "other"
        subprocess.run(["git", "worktree", "add", "-q", str(other)], cwd=self.repo, check=True, capture_output=True)
        self.assertEqual(self.run_verify(other), (0, "", []))

    def test_missing_witness_read_from_stored_receipts(self):
        self.run_verify()
        self.write("tests/test_a.py", TESTS.replace("def refuses_NoSelf(): pass\n", ""))
        self.assertEqual(self.run_verify(), (1, "FAIL check NoSelf: no refuses_NoSelf test\n", []))

    def test_missed_expect_read_from_stored_receipt(self):
        self.write(CHECK, CHECK_A % 1)
        self.assertEqual(self.run_verify()[:2], (1, "FAIL check NoSelf: expect 1 missed\n"))
        self.assertEqual(self.run_verify(), (1, "FAIL check NoSelf: expect 1 missed\n", []))

    def test_parse_failure_runs_every_time(self):
        self.write(CHECK, CHECK_A % 0 + "check NoSelf for 2 expect 0 }\n")
        want = (1, "FAIL spec/m/check.als: did not parse\n")
        self.assertEqual(self.run_verify()[:2], want)
        self.assertEqual(self.run_verify(), (*want, [CHECK]))

    def test_store_holds_only_receipts(self):
        self.run_verify()
        files = [p for p in self.store().rglob("*") if p.is_file()]
        self.assertEqual(sorted(p.name for p in files), ["receipt.json"] * 2)

    def test_broken_receipt_is_absent(self):
        self.run_verify()
        key = receipt.model_key(CHECK, lambda path: receipt.read_file(str(self.repo / path)))
        stored = self.store() / key / "receipt.json"
        stored.write_bytes(stored.read_bytes()[:stored.stat().st_size // 2])
        self.assertEqual(self.run_verify(), (0, "", [CHECK]))


if __name__ == "__main__":
    unittest.main()

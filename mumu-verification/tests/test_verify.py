"""What `verify.sh` answers for a repo: each missed expect, missing expect and unmatched witness named, then the suite.

Run: python3 -m unittest discover mumu-verification/tests
"""
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

VERIFY = pathlib.Path(__file__).resolve().parent.parent / "skills" / "spec" / "scripts" / "verify.sh"
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
    "no model, suite": ((None, {}, "false"), (1, "no model\nFAIL tests: false\n")),
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


if __name__ == "__main__":
    unittest.main()

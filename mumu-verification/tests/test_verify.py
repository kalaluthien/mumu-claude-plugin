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
MODEL = "sig A { f: set A }\nassert NoSelf { no a: A | a in a.f }\nfact { no a: A | a in a.f }\nrun {} for 2 expect 1\n"
GOOD, WITNESS = "check NoSelf for 2 expect 0\n", "def refuses_NoSelf(): pass\n"
NONE = "FAIL check NoSelf: no refuses_NoSelf test\n"
CASES = {  # name: (check.als tail or None for no spec, {file: text}, suite command), (exit, stdout)
    "passes": ((GOOD, {"test_m.py": WITNESS}, "true"), (0, "")),
    "no model": ((None, {}, "true"), (0, "no model\n")),
    "parse": (("check NoSelf for 2 expect 0 }\n", {"test_m.py": WITNESS}, "true"), (1, "FAIL spec/m/check.als: did not parse\n")),
    "no expect": (("check NoSelf for 2\n", {"test_m.py": WITNESS}, "true"), (1, "FAIL check NoSelf: no expect\n")),
    "missed expect": (("check NoSelf for 2 expect 1\n", {"test_m.py": WITNESS}, "true"), (1, "FAIL check NoSelf: expect 1 missed\n")),
    "no witness": ((GOOD, {}, "true"), (1, NONE)),
    "stale witness": ((GOOD, {"test_m.py": WITNESS + "refuses_Gone\n"}, "true"), (1, "FAIL test refuses_Gone: names no check\n")),
    "witness in docs or build": ((GOOD, {"docs/test_a.py": WITNESS, "app/build/test_a.py": WITNESS}, "true"), (1, NONE)),
    "witness in no test file": ((GOOD, {"src/a.py": WITNESS}, "true"), (1, NONE)),
    "witness in tests/": ((GOOD, {"tests/test_a.py": WITNESS}, "true"), (0, "")),
    "witness in androidTest/": ((GOOD, {"app/src/androidTest/k/A.kt": WITNESS}, "true"), (0, "")),
    "witness in *Test.kt": ((GOOD, {"src/k/ATest.kt": WITNESS}, "true"), (0, "")),
    "suite": ((GOOD, {"test_m.py": WITNESS}, "false"), (1, "FAIL tests: false\n")),
    "no model, suite": ((None, {}, "false"), (1, "no model\nFAIL tests: false\n")),
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
                p = subprocess.run([VERIFY], cwd=repo, capture_output=True, text=True,
                                   env={**os.environ, "VERIFY_TESTS": suite})
                self.assertEqual((p.returncode, p.stdout), want)


if __name__ == "__main__":
    unittest.main()

"""What `verify.sh` answers for a repo: each missed expect, missing expect and unmatched witness named, then the suite.

Run: python3 -m unittest discover mumu-verification/tests
"""
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

VERIFY = pathlib.Path(__file__).resolve().parent.parent / "skills" / "test" / "assets" / "verify.sh"
MODEL = "sig A { f: set A }\nassert NoSelf { no a: A | a in a.f }\nfact { no a: A | a in a.f }\nrun {} for 2 expect 1\n"
GOOD, WITNESS = "check NoSelf for 2 expect 0\n", "def refuses_NoSelf(): pass\n"
CASES = {  # name: (check.als tail or None for no spec, test file, suite command), (exit, stdout)
    "passes": ((GOOD, WITNESS, "true"), (0, "")),
    "no model": ((None, "", "true"), (0, "no model\n")),
    "parse": (("check NoSelf for 2 expect 0 }\n", WITNESS, "true"), (1, "FAIL spec/m/check.als: did not parse\n")),
    "no expect": (("check NoSelf for 2\n", WITNESS, "true"), (1, "FAIL check NoSelf: no expect\n")),
    "missed expect": (("check NoSelf for 2 expect 1\n", WITNESS, "true"), (1, "FAIL check NoSelf: expect 1 missed\n")),
    "no witness": ((GOOD, "", "true"), (1, "FAIL check NoSelf: no refuses_NoSelf test\n")),
    "stale witness": ((GOOD, WITNESS + "refuses_Gone\n", "true"), (1, "FAIL test refuses_Gone: names no check\n")),
    "suite": ((GOOD, WITNESS, "false"), (1, "FAIL tests: false\n")),
    "no model, suite": ((None, "", "false"), (1, "no model\nFAIL tests: false\n")),
}


@unittest.skipUnless(shutil.which("alloy"), "alloy not on PATH")
class Verify(unittest.TestCase):
    def test_cases(self):
        for name, ((check, tests, suite), want) in CASES.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as repo:
                os.makedirs(f"{repo}/spec/m")
                shutil.copy(VERIFY, f"{repo}/spec/verify.sh")
                if check is not None:
                    pathlib.Path(repo, "spec/m/check.als").write_text(MODEL + check)
                pathlib.Path(repo, "test_m.py").write_text(tests)
                p = subprocess.run([f"{repo}/spec/verify.sh"], capture_output=True, text=True,
                                   env={**os.environ, "VERIFY_TESTS": suite})
                self.assertEqual((p.returncode, p.stdout), want)


if __name__ == "__main__":
    unittest.main()

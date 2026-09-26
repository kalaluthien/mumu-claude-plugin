"""`decide.py` run against a fake gh on PATH that holds one issue body and logs each comment and edit.

Run: python3 -m unittest discover mumu-team/tests
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

BIN = pathlib.Path(__file__).resolve().parent.parent / "bin"
URL = "https://github.com/o/r/issues/12"
BODY = "## Goal\n\nKeep `## Goal` text as is.\n\n## Definition of done\n\n- old check → old pass\n\n## Notes\n\nkept\n"

FAKE_GH = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
d, a = pathlib.Path(os.environ["FAKE"]), sys.argv[1:]
stdin = sys.stdin.read() if "--body-file" in a else None
with open(d / "calls", "a") as f:
    f.write(json.dumps(a + [stdin]) + "\n")
if (d / "fail").exists() and a[:2] == ["issue", "edit"]:
    sys.exit("edit refused")
if a[:2] == ["issue", "view"]:
    print((d / "body").read_text())
elif a[:2] == ["issue", "edit"]:
    (d / "body").write_text(stdin)
elif a[:2] == ["issue", "comment"]:
    print(a[2] + "#issuecomment-1")
'''


class Decide(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "gh").write_text(FAKE_GH)
        (self.tmp / "gh").chmod(0o755)
        (self.tmp / "body").write_text(BODY)
        (self.tmp / "criteria").write_text("- new check → new pass\n- second → pass\n")

    def decide(self, text, *args):
        env = dict(os.environ, FAKE=str(self.tmp), PATH=f"{self.tmp}:{os.environ['PATH']}")
        done = subprocess.run([sys.executable, str(BIN / "decide.py"), URL, *args], input=text, env=env,
                              capture_output=True, text=True, timeout=30)
        log = self.tmp / "calls"
        return done, [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []

    def comments(self, calls):
        return [c[-1] for c in calls if c[:2] == ["issue", "comment"]]

    def test_posts_one_comment_opening_decided_and_leaves_the_body(self):
        for text in ("use the name fix-login", "DECIDED: use the name fix-login"):
            with self.subTest(text=text):
                (self.tmp / "calls").unlink(missing_ok=True)
                done, calls = self.decide(text)
                self.assertEqual(done.returncode, 0, done.stderr)
                [comment] = self.comments(calls)
                self.assertEqual(comment.splitlines()[0], "DECIDED: use the name fix-login")
                self.assertFalse([c for c in calls if c[:2] == ["issue", "edit"]])
        self.assertEqual((self.tmp / "body").read_text(), BODY)

    def test_criteria_replace_only_the_definition_of_done(self):
        done, calls = self.decide("drop the old check", "--criteria", str(self.tmp / "criteria"))
        self.assertEqual(done.returncode, 0, done.stderr)
        body = (self.tmp / "body").read_text()
        self.assertTrue(body.startswith("## Goal\n\nKeep `## Goal` text as is.\n\n## Definition of done\n\n"), body)
        self.assertIn("- new check → new pass\n- second → pass\n", body)
        self.assertNotIn("old check", body)
        self.assertIn("## Notes\n\nkept", body)
        self.assertEqual(self.comments(calls)[0].splitlines()[0], "DECIDED: drop the old check")
        edit = next(i for i, c in enumerate(calls) if c[:2] == ["issue", "edit"])
        self.assertLess(edit, next(i for i, c in enumerate(calls) if c[:2] == ["issue", "comment"]))

    def test_a_failed_edit_posts_no_comment(self):
        (self.tmp / "fail").touch()
        done, calls = self.decide("x", "--criteria", str(self.tmp / "criteria"))
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual(self.comments(calls), [])

    def test_no_decision_posts_nothing(self):
        done, calls = self.decide("  \n")
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()

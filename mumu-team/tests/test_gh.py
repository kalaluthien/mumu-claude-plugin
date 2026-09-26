"""`lib/gh.py` against a fake `gh` that logs its arguments and prints what `$FAKE_OUT` holds.

Run: python3 -m unittest discover mumu-team/tests
"""
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import gh  # noqa: E402

FAKE = r'''#!/usr/bin/env python3
import json, os, sys
open(os.environ["FAKE_LOG"], "a").write(json.dumps(sys.argv[1:]) + "\n")
print(os.environ.get("FAKE_OUT", ""))
sys.exit(int(os.environ.get("FAKE_EXIT", 0)))
'''


class Gh(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "gh").write_text(FAKE)
        (self.tmp / "gh").chmod(0o755)
        self.log = self.tmp / "log"
        self.env = {"PATH": f"{self.tmp}:{os.environ['PATH']}", "FAKE_LOG": str(self.log)}

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_repo_reads_one_field(self):
        with mock.patch.dict(os.environ, {**self.env, "FAKE_OUT": "main"}):
            self.assertEqual(gh.repo("defaultBranchRef"), "main")
        self.assertEqual(self.calls(), [["repo", "view", "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name"]])

    def test_held_reads_urls_or_answers_none(self):
        with mock.patch.dict(os.environ, {**self.env, "FAKE_OUT": json.dumps([{"url": "u1"}])}):
            self.assertEqual(gh.held("."), ["u1"])
        for out, code in [("not json", "0"), ("[]", "1")]:
            with self.subTest(out=out), mock.patch.dict(os.environ, {**self.env, "FAKE_OUT": out, "FAKE_EXIT": code}):
                self.assertIsNone(gh.held("."))

    def test_failure_raises(self):
        with mock.patch.dict(os.environ, {**self.env, "FAKE_EXIT": "1"}):
            self.assertRaises(RuntimeError, gh.gh, "issue", "view", "u")


if __name__ == "__main__":
    unittest.main()

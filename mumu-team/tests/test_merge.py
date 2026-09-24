"""`merge.py` run against a fake `gh`: it merges only at the head a reviewer approved.

Run: python3 -m unittest discover mumu-team/tests
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

MERGE = pathlib.Path(__file__).resolve().parent.parent / "bin" / "merge.py"
URL = "https://github.com/o/r/pull/1"
HEAD, OLD = "a" * 40, "b" * 40

# `gh pr view` serves pr.json; `gh pr merge` logs its words and, like GitHub, refuses a pin that is not the head,
# read from `head` when present, so a test can move the head between the view and the merge.
FAKE = r'''#!/usr/bin/env python3
import json, pathlib, sys
d, a = pathlib.Path(__file__).parent, sys.argv[1:]
pr = json.loads((d / "pr.json").read_text())
if a[:2] == ["pr", "view"]:
    print(json.dumps(pr))
elif a[:2] == ["pr", "merge"]:
    (d / "merged").write_text(json.dumps(a))
    head = (d / "head").read_text() if (d / "head").exists() else pr["headRefOid"]
    if "--match-head-commit" in a and a[a.index("--match-head-commit") + 1] != head:
        sys.exit("head moved")
'''


def merge(comments, moved_to=None, reviews=(), url=URL):
    """Run merge.py on a PR at HEAD holding `comments`; `moved_to` moves the head once it is read. Return (result, merge words or None)."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    pr = {"headRefOid": HEAD, "comments": [{"body": b} for b in comments], "reviews": [{"body": b} for b in reviews]}
    (tmp / "pr.json").write_text(json.dumps(pr))
    if moved_to:
        (tmp / "head").write_text(moved_to)
    (tmp / "gh").write_text(FAKE)
    (tmp / "gh").chmod(0o755)
    env = dict(os.environ, PATH=f"{tmp}:{os.environ['PATH']}")
    result = subprocess.run([sys.executable, str(MERGE), url], capture_output=True, text=True, env=env)
    merged = tmp / "merged"
    return result, json.loads(merged.read_text()) if merged.exists() else None


class Merge(unittest.TestCase):
    def test_an_approval_at_the_head_squash_merges_pinned_to_it(self):
        for body in (f"APPROVED: {HEAD}", f"Approved {HEAD}", f"approved: {HEAD}", f"APPROVED {HEAD}\nchecked the tests"):
            with self.subTest(body=body):
                result, words = merge([body])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(words, ["pr", "merge", URL, "--squash", "--match-head-commit", HEAD])

    def test_an_approving_review_counts_too(self):
        result, words = merge([], reviews=[f"APPROVED: {HEAD}"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNotNone(words)

    def test_no_approval_is_refused_before_any_merge(self):
        for comments in ([], [f"FINDINGS: {HEAD}"], [f"not approved: {HEAD}"], [f"Approvedx {HEAD}"], [f"APPROVED: {HEAD} but"]):
            with self.subTest(comments=comments):
                result, words = merge(comments)
                self.assertNotEqual(result.returncode, 0)
                self.assertIsNone(words)
                self.assertIn(f"APPROVED: {HEAD}", result.stderr)

    def test_an_approval_at_an_old_sha_is_refused_before_any_merge(self):
        result, words = merge([f"APPROVED: {OLD}"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(words)

    def test_a_head_moved_after_the_read_is_refused_by_the_pin(self):
        result, words = merge([f"APPROVED: {HEAD}"], moved_to=OLD)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("head moved", result.stderr)

    def test_a_pr_not_named_by_its_url_is_refused(self):
        for arg in ("1", "o/r#1", "https://github.com/o/r/pull/1/files"):
            with self.subTest(arg=arg):
                result, words = merge([f"APPROVED: {HEAD}"], url=arg)
                self.assertNotEqual(result.returncode, 0)
                self.assertIsNone(words)


if __name__ == "__main__":
    unittest.main()

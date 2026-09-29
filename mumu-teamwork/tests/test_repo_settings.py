"""`skills/kickoff/scripts/repo-settings.py`, run against a fake `gh` that keeps a repository's settings in a file.

Run: uvx pytest mumu-teamwork/tests -q
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "skills" / "kickoff" / "scripts" / "repo-settings.py"

# `gh api` reads and writes `repo.json`, logs each write to `writes`, and answers 403 on any rulesets path,
# as GitHub does for a free plan's private repository.
FAKE_GH = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
d, a = pathlib.Path(os.environ["FAKE"]), sys.argv[1:]
repo = json.loads((d / "repo.json").read_text())
if a[:2] == ["repo", "view"]:
    print("main")
    sys.exit()
method = a[a.index("-X") + 1] if "-X" in a else "GET"
path = next(w for w in a[1:] if w.startswith("repos/"))
body = json.loads(sys.stdin.read()) if "--input" in a else None
if method != "GET":
    with open(d / "writes", "a") as f:
        f.write(json.dumps([method, path, body]) + "\n")
if "/rulesets" in path:
    sys.exit("gh: Upgrade to GitHub Pro or make this repository public to enable this feature. (HTTP 403)")
if path == "repos/{owner}/{repo}":
    if method == "PATCH":
        repo.update(body)
    print(json.dumps(repo))
elif path.endswith("/check-runs"):
    print(json.dumps({"check_runs": []}))
(d / "repo.json").write_text(json.dumps(repo))
'''

LIVE_REPO = {"allow_squash_merge": True, "allow_merge_commit": True, "allow_rebase_merge": True, "delete_branch_on_merge": False,
             "allow_auto_merge": False}


class RepoSettings(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp()).resolve()
        (self.tmp / "repo" / ".git").mkdir(parents=True)
        (self.tmp / "gh").write_text(FAKE_GH)
        (self.tmp / "gh").chmod(0o755)
        (self.tmp / "repo.json").write_text(json.dumps(LIVE_REPO))

    def run_it(self):
        (self.tmp / "writes").unlink(missing_ok=True)
        env = dict(os.environ, FAKE=str(self.tmp), PATH=f"{self.tmp}:{os.environ['PATH']}")
        done = subprocess.run([sys.executable, str(SCRIPT), str(self.tmp / "repo")], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        log = self.tmp / "writes"
        return done.stdout, [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def test_first_run_sets_squash_only_and_branch_deletion_despite_a_403_on_rulesets(self):
        out, writes = self.run_it()
        self.assertEqual(writes, [["PATCH", "repos/{owner}/{repo}", {"allow_squash_merge": True, "allow_merge_commit": False,
                                                                     "allow_rebase_merge": False, "delete_branch_on_merge": True}]])
        self.assertEqual(out.strip(), "changed: repository")

    def test_a_second_run_changes_nothing(self):
        self.run_it()
        out, writes = self.run_it()
        self.assertEqual(writes, [])
        self.assertEqual(out.strip(), "unchanged")


if __name__ == "__main__":
    unittest.main()

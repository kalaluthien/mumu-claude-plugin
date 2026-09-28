"""`skills/kickoff/scripts/repo-settings.py`, run against a fake `gh` that keeps a repository's settings and rulesets in files.

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

# `gh api` reads and writes `repo.json` and `rulesets.json` ({id: ruleset}), and logs each write to `writes`.
FAKE_GH = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
d, a = pathlib.Path(os.environ["FAKE"]), sys.argv[1:]
repo, rulesets = json.loads((d / "repo.json").read_text()), json.loads((d / "rulesets.json").read_text())
if a[:2] == ["repo", "view"]:
    print("main")
    sys.exit()
method = a[a.index("-X") + 1] if "-X" in a else "GET"
path = next(w for w in a[1:] if w.startswith("repos/"))
body = json.loads(sys.stdin.read()) if "--input" in a else None
if method != "GET":
    with open(d / "writes", "a") as f:
        f.write(json.dumps([method, path, body]) + "\n")
if path == "repos/{owner}/{repo}":
    if method == "PATCH":
        repo.update(body)
    print(json.dumps(repo))
elif path.endswith("/check-runs"):
    print(json.dumps({"check_runs": [{"name": n} for n in json.loads((d / "checks.json").read_text())]}))
elif path == "repos/{owner}/{repo}/rulesets":
    if method == "POST":
        rulesets["7"] = dict(body, id=7)
    print(json.dumps([{"id": r["id"], "name": r["name"]} for r in rulesets.values()]))
else:
    n = path.rsplit("/", 1)[1]
    if method == "PUT":
        rulesets[n] = dict(body, id=int(n))
    print(json.dumps(rulesets[n]))
(d / "repo.json").write_text(json.dumps(repo))
(d / "rulesets.json").write_text(json.dumps(rulesets))
'''

LIVE_REPO = {"allow_squash_merge": True, "allow_merge_commit": True, "allow_rebase_merge": True, "delete_branch_on_merge": False,
             "allow_auto_merge": False}
# The ruleset #239 created: all three merge methods, and a key GitHub adds that the script does not set.
OLD_RULESET = {"id": 3, "name": "mumu-default-branch", "target": "branch", "enforcement": "active", "bypass_actors": [],
               "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
               "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}, {"type": "pull_request", "parameters": {
                   "required_approving_review_count": 0, "dismiss_stale_reviews_on_push": False, "require_code_owner_review": False,
                   "require_last_push_approval": False, "required_review_thread_resolution": False,
                   "allowed_merge_methods": ["merge", "squash", "rebase"], "require_extra_approval_for_unattributed_changes": True}}]}


class RepoSettings(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp()).resolve()
        (self.tmp / "repo" / ".git").mkdir(parents=True)
        (self.tmp / "gh").write_text(FAKE_GH)
        (self.tmp / "gh").chmod(0o755)
        self.seed(LIVE_REPO, {}, [])

    def seed(self, repo, rulesets, checks):
        (self.tmp / "repo.json").write_text(json.dumps(repo))
        (self.tmp / "rulesets.json").write_text(json.dumps({str(r["id"]): r for r in rulesets.values()} if rulesets else {}))
        (self.tmp / "checks.json").write_text(json.dumps(checks))

    def run_it(self):
        (self.tmp / "writes").unlink(missing_ok=True)
        env = dict(os.environ, FAKE=str(self.tmp), PATH=f"{self.tmp}:{os.environ['PATH']}")
        done = subprocess.run([sys.executable, str(SCRIPT), str(self.tmp / "repo")], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        log = self.tmp / "writes"
        return done.stdout, [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def ruleset(self):
        return next(iter(json.loads((self.tmp / "rulesets.json").read_text()).values()))

    def test_first_run_sets_squash_only_branch_deletion_and_the_ruleset(self):
        out, writes = self.run_it()
        self.assertEqual([w[:2] for w in writes], [["PATCH", "repos/{owner}/{repo}"], ["POST", "repos/{owner}/{repo}/rulesets"]])
        self.assertEqual(writes[0][2], {"allow_squash_merge": True, "allow_merge_commit": False, "allow_rebase_merge": False,
                                        "delete_branch_on_merge": True})
        ruleset = writes[1][2]
        self.assertEqual((ruleset["name"], ruleset["enforcement"], ruleset["bypass_actors"]), ("mumu-default-branch", "active", []))
        self.assertEqual(ruleset["conditions"], {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}})
        self.assertEqual([r["type"] for r in ruleset["rules"]], ["deletion", "non_fast_forward", "pull_request"])
        self.assertEqual(ruleset["rules"][2]["parameters"]["allowed_merge_methods"], ["squash"])
        self.assertEqual(ruleset["rules"][2]["parameters"]["required_approving_review_count"], 0)
        self.assertIn("changed", out)

    def test_a_second_run_changes_nothing(self):
        self.run_it()
        out, writes = self.run_it()
        self.assertEqual(writes, [])
        self.assertEqual(out.strip(), "unchanged")

    def test_an_older_ruleset_is_updated_in_place(self):
        self.seed(LIVE_REPO, {"3": OLD_RULESET}, [])
        _, writes = self.run_it()
        self.assertEqual([w[:2] for w in writes], [["PATCH", "repos/{owner}/{repo}"], ["PUT", "repos/{owner}/{repo}/rulesets/3"]])
        self.assertEqual(self.ruleset()["rules"][2]["parameters"]["allowed_merge_methods"], ["squash"])
        self.assertEqual(self.run_it()[1], [])

    def test_checks_on_the_default_branch_are_required_up_to_date(self):
        self.seed(LIVE_REPO, {}, ["test", "lint"])
        self.run_it()
        [rule] = [r for r in self.ruleset()["rules"] if r["type"] == "required_status_checks"]
        self.assertEqual(rule["parameters"], {"strict_required_status_checks_policy": True,
                                              "required_status_checks": [{"context": "lint"}, {"context": "test"}]})
        self.assertEqual(self.run_it()[1], [])


if __name__ == "__main__":
    unittest.main()

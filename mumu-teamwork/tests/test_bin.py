"""The `bin/` commands, each run against fake `herdr`, `git` and `gh` commands on PATH that log every call.

Run: uvx pytest mumu-teamwork/tests -q
"""
import importlib.machinery
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
BIN = ROOT / "bin"
sys.path.insert(0, str(ROOT / "lib"))
from scope import pattern  # noqa: E402
ISSUE_URL = "https://github.com/o/r/issues/12"
ISSUE_BODY = "## Goal\n\nKeep `## Goal` text as is.\n\n## Definition of done\n\n- old check → old pass\n\n## Notes\n\nkept\n"

DECIDE_GH = r'''#!/usr/bin/env python3
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
        (self.tmp / "gh").write_text(DECIDE_GH)
        (self.tmp / "gh").chmod(0o755)
        (self.tmp / "body").write_text(ISSUE_BODY)
        (self.tmp / "criteria").write_text("- new check → new pass\n- second → pass\n")

    def decide(self, text, *args):
        env = dict(os.environ, FAKE=str(self.tmp), PATH=f"{self.tmp}:{os.environ['PATH']}")
        done = subprocess.run([sys.executable, str(BIN / "decision-post.py"), ISSUE_URL, *args], input=text, env=env,
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
        self.assertEqual((self.tmp / "body").read_text(), ISSUE_BODY)

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


MERGE = pathlib.Path(__file__).resolve().parent.parent / "bin" / "pr-merge.py"
PR_URL = "https://github.com/o/r/pull/1"
HEAD, OLD = "a" * 40, "b" * 40

# `gh pr view` serves pr.json; `gh pr merge` logs its words and, like GitHub, refuses a pin that is not the head,
# read from `head` when present, so a test can move the head between the view and the merge.
MERGE_GH = r'''#!/usr/bin/env python3
import base64, json, pathlib, sys
d, a = pathlib.Path(__file__).parent, sys.argv[1:]
pr = json.loads((d / "pr.json").read_text())
if a[:2] == ["pr", "view"]:
    print(json.dumps(pr))
elif a[0] == "api" and a[1].startswith("repos/o/r/contents/checks.json"):
    if "mapping" not in pr:
        sys.exit("gh: Not Found (HTTP 404)")
    print(json.dumps({"content": base64.b64encode(json.dumps(pr["mapping"]).encode()).decode()}))
elif a[0] == "api" and a[1].startswith("repos/o/r/git/trees/"):
    print(json.dumps({"tree": [{"path": n} for n in pr.get("tree", [])], "truncated": False}))
elif a[0] == "api":
    since = a[1].removeprefix("repos/o/r/compare/").split("...")[0]
    if since == "main":
        files = pr.get("files", [])
    elif since in pr.get("since", {}):
        files = pr["since"][since]
    else:
        files = pr.get("base_files", [])
    status = "ahead" if since == "main" or since in pr.get("since", {}) else "diverged"
    files = [f if isinstance(f, dict) else {"filename": f} for f in files]
    print(json.dumps({"behind_by": pr.get("behind", 0), "status": status, "files": files}))
elif a[:2] == ["issue", "view"]:
    print(json.dumps({"body": pr.get("issues", {}).get(a[2], "## Goal\nx\n")}))
elif a[:2] == ["pr", "merge"]:
    (d / "merged").write_text(json.dumps(a))
    head = (d / "head").read_text() if (d / "head").exists() else pr["headRefOid"]
    if "--match-head-commit" in a and a[a.index("--match-head-commit") + 1] != head:
        sys.exit("head moved")
'''


SHARED = "## Goal\nx\n\n## Shares\n| share | DoD | after | with |\n| --- | --- | --- | --- |\n| a | D1 | | b: interface agreed first |\n"


def merge(comments, moved_to=None, reviews=(), url=PR_URL, title="t", body="Closes #3", commits=(), issues=None, behind=0,
          head=HEAD, cwd=None, files=(), base_files=(), **scoped):
    """Run pr-merge.py in `cwd` on a PR at `head` holding `comments`, each a body or a comment's dict; `moved_to` moves the head once
    it is read, `issues` maps an issue url to its body, `behind` counts the base's commits the head lacks. Return (result, merge
    words or None)."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    notes = lambda bodies: [b if isinstance(b, dict) else {"body": b} for b in bodies]
    pr = {"headRefOid": head, "comments": notes(comments), "reviews": notes(reviews),
          "title": title, "body": body, "commits": [{"messageHeadline": h, "messageBody": b} for h, b in commits],
          "baseRefName": "main", "issues": issues or {}, "behind": behind,
          "files": list(files), "base_files": list(base_files), **scoped}
    (tmp / "pr.json").write_text(json.dumps(pr))
    if moved_to:
        (tmp / "head").write_text(moved_to)
    (tmp / "gh").write_text(MERGE_GH)
    (tmp / "gh").chmod(0o755)
    env = dict(os.environ, PATH=f"{tmp}:{os.environ['PATH']}")
    result = subprocess.run([sys.executable, str(MERGE), url], capture_output=True, text=True, env=env, cwd=cwd or tmp)
    merged = tmp / "merged"
    return result, json.loads(merged.read_text()) if merged.exists() else None


class Merge(unittest.TestCase):
    def test_an_approval_at_the_head_squash_merges_pinned_to_it(self):
        for body in (f"APPROVED: {HEAD}", f"Approved {HEAD}", f"approved: {HEAD}", f"APPROVED {HEAD}\nchecked the tests"):
            with self.subTest(body=body):
                result, words = merge([body])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(words, ["pr", "merge", PR_URL, "--squash", "--match-head-commit", HEAD])

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

    def test_a_closing_keyword_on_a_task_with_shares_is_refused_wherever_it_is(self):
        """`## Shares` on the task named by `Part of` or by the keyword itself refuses any closing keyword, in any of the three places."""
        task, other = "https://github.com/o/r/issues/5", "https://github.com/o/r/issues/6"
        cases = {"title": dict(title="a: fix it, closes #6", body="Part of #5"),
                 "body": dict(body=f"Part of {task}\n\nFixes: #6"),
                 "commit": dict(body="Part of #5", commits=[("a: step", "resolved o/r#6")]),
                 "the task itself": dict(body="Closes #5")}
        for where, pr in cases.items():
            with self.subTest(where=where):
                result, words = merge([f"APPROVED: {HEAD}"], issues={task: SHARED, other: "## Goal\nx\n"}, **pr)
                self.assertNotEqual(result.returncode, 0)
                self.assertIsNone(words)
                self.assertIn(task, result.stderr)

    def test_a_task_with_shares_merges_as_part_of_it(self):
        result, words = merge([f"APPROVED: {HEAD}"], title="a: add x", body="Part of #5", commits=[("a: add x", "")],
                              issues={"https://github.com/o/r/issues/5": SHARED})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNotNone(words)

    def test_a_task_without_shares_still_merges_with_closes(self):
        result, words = merge([f"APPROVED: {HEAD}"], body="Closes #5", commits=[("fix #5", "closes #5")],
                              issues={"https://github.com/o/r/issues/5": "## Goal\nx\n\n## Definition of done\n- a → b\n"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNotNone(words)

    def test_a_body_naming_no_task_over_30_lines_is_refused_before_any_merge(self):
        big = [{"filename": "a.py", "additions": 20, "deletions": 11}]
        for body in ("", "criteria only", "see #3"):
            with self.subTest(body=body):
                result, words = merge([f"APPROVED: {HEAD}"], body=body, files=big)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("names no task", result.stderr)
                self.assertIsNone(words)
        for body in ("Closes #3\n\n| D1 | pass |", "Part of #3", "Fixes https://github.com/o/r/issues/3"):
            with self.subTest(body=body):
                result, words = merge([f"APPROVED: {HEAD}"], body=body)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_head_behind_its_base_is_refused_before_any_merge(self):
        _, words = merge([f"APPROVED: {HEAD}"], behind=0)
        self.assertIsNotNone(words)
        result, words = merge([f"APPROVED: {HEAD}"], behind=2)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(words)
        self.assertIn("merge it in", result.stderr)

    def test_a_behind_refusal_names_the_paths_both_sides_change(self):
        """Paths the PR and the base's new commits both change ask for a rerun; none shared skips it."""
        result, words = merge([f"APPROVED: {HEAD}"], behind=2, files=["a.py", "b.md"], base_files=["b.md", "c.py"])
        self.assertIsNone(words)
        self.assertIn("b.md", result.stderr)
        self.assertNotIn("a.py", result.stderr)
        self.assertIn("rerun every check on the merged tree", result.stderr)
        result, words = merge([f"APPROVED: {HEAD}"], behind=2, files=["a.py"], base_files=["c.py"])
        self.assertIsNone(words)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("merge it in, push and run pr-merge.py again; no rerun needed", result.stderr)


GIT_ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")


def carry_git(repo, *argv):
    """stdout of `git <argv>` in `repo`, with no hook, signing or user config."""
    return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", *argv], cwd=repo, env=GIT_ENV,
                          capture_output=True, text=True, check=True).stdout.strip()


def commit(repo, message, **files):
    """Write each file, commit them as `message`, and return the new sha."""
    for name, text in files.items():
        (repo / name).write_text(text)
    carry_git(repo, "add", "-A")
    carry_git(repo, "commit", "-q", "--allow-empty", "-m", message)
    return carry_git(repo, "rev-parse", "HEAD")


def remerge(repo, approved, main, **files):
    """Merge `main` into `approved` again on a detached head, writing each file into the merge commit; return its sha."""
    carry_git(repo, "checkout", "-q", "--detach", approved)
    carry_git(repo, "merge", "-q", "--no-ff", "--no-commit", main)
    return commit(repo, f"Merge {main}", **files)


class MergeCarry(unittest.TestCase):
    """An `APPROVED: <A>` carries to the head only across merges of origin/main that keep the diff from the merge base."""

    def setUp(self):
        self.repo = repo = pathlib.Path(tempfile.mkdtemp())
        carry_git(repo, "init", "-q", "-b", "main")
        self.base = commit(repo, "base", **{"base.txt": "x\n"})
        carry_git(repo, "checkout", "-q", "-b", "pr")
        self.approved = commit(repo, "pr change", **{"pr.txt": "  indented\n"})
        carry_git(repo, "checkout", "-q", "main")
        self.main = commit(repo, "main moves on", **{"main.txt": "y\n"})
        carry_git(repo, "update-ref", "refs/remotes/origin/main", self.main)
        self.head = remerge(repo, self.approved, self.main)

    def run_merge(self, head, comments=None):
        return merge(comments or [f"APPROVED: {self.approved}"], head=head, cwd=self.repo)

    def assertRefused(self, result, words, head, approved=None):
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(words)
        self.assertIn(approved or self.approved, result.stderr)
        self.assertIn(head, result.stderr)

    def test_an_approval_carries_across_a_merge_of_main(self):
        result, words = self.run_merge(self.head)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(words, ["pr", "merge", PR_URL, "--squash", "--match-head-commit", self.head])

    def test_a_changed_patch_does_not_carry(self):
        for name, text in (("an extra edit", "  indented\nmore\n"), ("a re-indent", "    indented\n")):
            with self.subTest(name=name):
                head = remerge(self.repo, self.approved, self.main, **{"pr.txt": text})
                result, words = self.run_merge(head)
                self.assertRefused(result, words, head)
                self.assertIn("patch-id", result.stderr)

    def test_a_commit_on_the_path_that_is_no_merge_of_main_does_not_carry(self):
        carry_git(self.repo, "checkout", "-q", "--detach", self.head)
        on_top = commit(self.repo, "empty, so the patch is unchanged")
        carry_git(self.repo, "checkout", "-q", "--detach", self.approved)
        side = commit(self.repo, "a side branch off the approved commit")
        merged_side = remerge(self.repo, self.approved, side)
        for name, head in (("a plain commit", on_top), ("a merge of a branch not on main", merged_side)):
            with self.subTest(name=name):
                result, words = self.run_merge(head)
                self.assertRefused(result, words, head)
                self.assertIn("not a merge", result.stderr)

    def test_an_approval_of_no_ancestor_does_not_carry(self):
        """A force-pushed head with the same patch: a rewritten A is no ancestor of it."""
        carry_git(self.repo, "checkout", "-q", "--detach", self.base)
        rewritten = commit(self.repo, "pr change, rewritten", **{"pr.txt": "  indented\n"})
        head = remerge(self.repo, rewritten, self.main)
        result, words = self.run_merge(head)
        self.assertRefused(result, words, head)
        self.assertIn("not an ancestor", result.stderr)

    def test_findings_newer_than_the_approval_refuse(self):
        approve = {"body": f"APPROVED: {self.approved}", "createdAt": "2026-01-01T00:00:01Z"}
        findings = {"body": f"FINDINGS: {self.approved}\n- a defect", "createdAt": "2026-01-01T00:00:02Z"}
        result, words = self.run_merge(self.head, [findings, approve])
        self.assertRefused(result, words, self.head)
        self.assertIn("FINDINGS", result.stderr)
        again = {"body": f"APPROVED: {self.head}", "submittedAt": "2026-01-01T00:00:03Z"}
        result, words = merge([findings, approve], reviews=[again], head=self.head, cwd=self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_findings_newer_than_an_approval_of_the_head_refuse(self):
        result, words = merge([f"APPROVED: {HEAD}", f"FINDINGS: {HEAD}"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(words)
        self.assertIn(HEAD, result.stderr)

    def test_an_unreadable_or_empty_diff_does_not_carry(self):
        carry_git(self.repo, "checkout", "-q", "--detach", self.base)
        empty = commit(self.repo, "no change")
        head = remerge(self.repo, empty, self.main)
        result, words = merge([f"APPROVED: {empty}"], head=head, cwd=self.repo)
        self.assertRefused(result, words, head, empty)
        self.assertIn("empty", result.stderr)
        carry_git(self.repo, "update-ref", "-d", "refs/remotes/origin/main")
        result, words = self.run_merge(self.head)
        self.assertRefused(result, words, self.head)
        self.assertIn("cannot be read", result.stderr)

    def test_step_4_resumes_the_judge_only_when_the_merge_is_refused_again(self):
        step = next(l for l in (ROOT / "skills/kickoff/references/worker-playbook.md").read_text().splitlines() if l.startswith("4. "))
        after = step[step.index("merge the default branch in"):]
        self.assertRegex(after.split(". ")[0], r"`merge` again.*only when `pr-merge\.py` names the judge, resume it")

    def test_the_approval_of_pull_request_268_carries_across_its_merge_of_main(self):
        """Replays #268: `APPROVED: A`, then head H merges the non-empty 459d5b9 of main in."""
        approved, head, main = "a0693293473f796f93ec5b841f75c2df13d1dee7", "156135ca449009d226c7ead34db16e0a60124cef", "459d5b9"
        repo = pathlib.Path(tempfile.mkdtemp())
        carry_git(repo, "init", "-q")
        common = carry_git(ROOT, "rev-parse", "--path-format=absolute", "--git-common-dir")
        (repo / ".git/objects/info/alternates").write_text(f"{common}/objects\n")
        carry_git(repo, "remote", "add", "origin", carry_git(ROOT, "remote", "get-url", "origin"))
        try:
            carry_git(repo, "fetch", "-q", "origin", "refs/pull/268/head")
        except subprocess.CalledProcessError as e:
            self.skipTest(f"offline: git fetch origin refs/pull/268/head failed: {e.stderr.strip()}")
        carry_git(repo, "update-ref", "refs/remotes/origin/main", main)
        result, words = merge([f"APPROVED: {approved}"], head=head, cwd=repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(words[-1], head)
        carry_git(repo, "checkout", "-q", "--detach", head)
        on_top = commit(repo, "a plain commit on top")
        probe = "experiments/263/ruleB1.md"
        cases = {"a plain commit on top": on_top,
                 "an extra edit in the merge": remerge(repo, approved, main, **{probe: "Probe ruleB1 for #263.\nmore\n"}),
                 "a re-indent in the merge": remerge(repo, approved, main, **{probe: "  Probe ruleB1 for #263.\n"})}
        for name, bad in cases.items():
            with self.subTest(name=name):
                result, words = merge([f"APPROVED: {approved}"], head=bad, cwd=repo)
                self.assertNotEqual(result.returncode, 0)
                self.assertIsNone(words)
                self.assertIn(approved, result.stderr)
                self.assertIn(bad, result.stderr)


# State lives in files under $CLOSE_HERDR: `alive` while the session runs, `exiting` counts the polls a plain /exit takes to leave herdr's list,
# and `screen` names the exit dialog showing. /exit shows the `background` dialog when that file exists, else the screen a `draft`
# file names; each key moves between screens as the live Claude Code v2.1.282 does (issue #79's comment), and `frozen` ignores keys.
CLOSE_HERDR = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
d, a = pathlib.Path(os.environ["CLOSE_HERDR"]), sys.argv[1:]
with open(d / "calls", "a") as f:
    f.write(json.dumps(a) + "\n")
alive, screen, exiting = d / "alive", d / "screen", d / "exiting"
SCREENS = {
    "background": " Background work is running\n ❯ 1. Exit\n   2. Keep running",
    "unsent": "  You have 1 unsent feedback draft\n  Enter to review & send · Esc to discard and exit",
    "list": "   Feedback drafts\n   ❯ probe draft   idea · 1m\n   Enter to review · d to discard · Esc to close",
    "review": "   Feedback drafts\n   ❯ Send feedback\n   ↑/↓ to move · Enter to send · d to discard · Esc to later",
    "empty": "   Feedback drafts\n   No feedback drafts queued.\n   Any key closes this panel.\n   Esc to close",
}
MOVES = {("background", "enter"): None, ("unsent", "esc"): None, ("unsent", "enter"): "list",
         ("list", "enter"): "review", ("list", "d"): "empty", ("review", "d"): "empty", ("empty", "esc"): None}
if a[:2] == ["agent", "list"]:
    if exiting.exists():
        left = int(exiting.read_text()) - 1
        exiting.write_text(str(left))
        if not left:
            exiting.unlink()
            alive.unlink()
    status = "blocked" if (d / "blocked").exists() and screen.exists() else "working" if (d / "working").exists() else "idle"
    agent = {"name": "close-7", "pane_id": "w1:p7", "tab_id": "w1:t7", "agent_status": status}
    agents = [agent] if alive.exists() else []
    print(json.dumps({"result": {"agents": agents}}))
elif a[:2] == ["agent", "prompt"] and (d / "blocked").exists() and screen.exists():
    print(json.dumps({"error": {"code": "agent_blocked"}}))
    sys.exit(1)
elif a[:2] == ["agent", "read"] and "--lines" in a and (d / "working").exists():
    print(json.dumps({"error": {"code": "agent_not_idle"}}))
    sys.exit(1)
elif a[:2] == ["agent", "prompt"] and a[3] == "/exit" and not (d / "stuck").exists():
    if (d / "background").exists():
        screen.write_text("background")
    elif (d / "draft").exists():
        screen.write_text((d / "draft").read_text() or "unsent")
    else:
        exiting.write_text("3")
elif a[:2] == ["agent", "read"]:
    print(SCREENS[screen.read_text()] if screen.exists() else "❯")
elif a[:2] == ["agent", "send-keys"] and screen.exists() and not (d / "frozen").exists():
    key = (screen.read_text(), a[3])
    if key in MOVES:
        if MOVES[key] is None:
            screen.unlink()
            alive.unlink()
        else:
            screen.write_text(MOVES[key])
elif a[:2] == ["tab", "list"]:
    print(json.dumps({"result": {"tabs": [{"label": "close-7", "tab_id": "w1:t7"}, {"label": "other-8", "tab_id": "w1:t8"}]}}))
'''


class WorkerClose(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "herdr").write_text(CLOSE_HERDR)
        (self.tmp / "herdr").chmod(0o755)
        (self.tmp / "alive").touch()

    def close(self):
        env = dict(os.environ, CLOSE_HERDR=str(self.tmp), PATH=f"{self.tmp}:{os.environ['PATH']}",
                   WORKER_CLOSE_TIMEOUT="1", WORKER_CLOSE_POLL="0.01")
        done = subprocess.run([sys.executable, str(BIN / "session-close.py"), "close-7"],
                              env=env, capture_output=True, text=True, timeout=30)
        calls = [json.loads(l) for l in (self.tmp / "calls").read_text().splitlines()]
        return done, calls

    def assertClosed(self, done, calls):
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, "closed close-7\n")
        self.assertFalse((self.tmp / "alive").exists(), "session left running")
        self.assertEqual([c for c in calls if c[:2] == ["tab", "close"]], [["tab", "close", "w1:t7"]])

    def test_exit_without_dialog_sends_no_keys(self):
        done, calls = self.close()
        self.assertClosed(done, calls)
        self.assertIn(["agent", "prompt", "w1:p7", "/exit"], calls)
        self.assertFalse([c for c in calls if c[:2] == ["agent", "send-keys"]])

    def test_dialog_answered_with_one_enter_after_it_shows(self):
        (self.tmp / "background").touch()
        done, calls = self.close()
        self.assertClosed(done, calls)
        keys = [i for i, c in enumerate(calls) if c[:2] == ["agent", "send-keys"]]
        self.assertEqual([calls[i] for i in keys], [["agent", "send-keys", "w1:p7", "enter"]])
        self.assertLess(calls.index(["agent", "prompt", "w1:p7", "/exit"]), keys[0])
        self.assertLess(keys[0], calls.index(["tab", "close", "w1:t7"]), "tab closed before the session exited")

    def test_blocked_at_dialog_answers_it_without_exit(self):
        (self.tmp / "blocked").touch()
        (self.tmp / "screen").write_text("background")
        done, calls = self.close()
        self.assertClosed(done, calls)
        self.assertFalse([c for c in calls if c[:2] == ["agent", "prompt"]])
        self.assertEqual(self.keys(calls), [["enter"]])

    def test_working_agent_read_from_visible_screen(self):
        (self.tmp / "working").touch()
        (self.tmp / "background").touch()
        done, calls = self.close()
        self.assertClosed(done, calls)
        self.assertIn(["agent", "read", "w1:p7", "--source", "visible"], calls)
        self.assertEqual(self.keys(calls), [["enter"]])

    def keys(self, calls):
        return [c[3:] for c in calls if c[:2] == ["agent", "send-keys"]]

    def test_feedback_draft_discarded_with_one_esc(self):
        (self.tmp / "draft").touch()
        done, calls = self.close()
        self.assertClosed(done, calls)
        self.assertEqual(self.keys(calls), [["esc"]])

    def test_drafts_list_discarded_then_empty_panel_closed(self):
        (self.tmp / "draft").write_text("list")
        done, calls = self.close()
        self.assertClosed(done, calls)
        self.assertEqual(self.keys(calls), [["d"], ["esc"]])

    def test_draft_review_discarded_never_sent(self):
        (self.tmp / "draft").write_text("review")
        done, calls = self.close()
        self.assertClosed(done, calls)
        self.assertEqual(self.keys(calls), [["d"], ["esc"]])
        self.assertNotIn(["enter"], self.keys(calls))

    def test_each_dialog_answered_at_most_once(self):
        (self.tmp / "draft").touch()
        (self.tmp / "frozen").touch()
        done, calls = self.close()
        self.assertEqual(done.returncode, 1)
        self.assertEqual(self.keys(calls), [["esc"]])

    def test_session_already_gone_still_closes_its_tab(self):
        (self.tmp / "alive").unlink()
        done, calls = self.close()
        self.assertClosed(done, calls)
        self.assertFalse([c for c in calls if c[:2] == ["agent", "prompt"]])

    def test_session_that_never_exits_keeps_its_tab(self):
        (self.tmp / "stuck").touch()
        done, calls = self.close()
        self.assertEqual(done.returncode, 1)
        self.assertIn("herdr agent read w1:p7", done.stderr)
        self.assertFalse([c for c in calls if c[:2] == ["tab", "close"]])


PANE = "w1:p1"
ISSUE = "https://github.com/o/r/issues/7"

# One fake for all three tools, chosen by the name it is called as; state lives in files under $START_FAKE.
START_FAKE = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
d, tool, a = pathlib.Path(os.environ["START_FAKE"]), pathlib.Path(sys.argv[0]).name, sys.argv[1:]
with open(d / "calls", "a") as f:
    f.write(json.dumps([tool] + a) + "\n")
blocked = (d / "trust").exists() and not (d / "answered").exists()
if tool == "gh":
    prs = d / ("open_prs" if "open" in a else "prs")
    if a[:2] == ["issue", "view"]:
        print((d / "issue").read_text() if (d / "issue").exists() else json.dumps({"state": "OPEN", "labels": [], "body": ""}))
    elif a[:1] == ["api"] and a[1].endswith("/dependencies/blocked_by"):
        print((d / "blockers").read_text() if (d / "blockers").exists() else "[]")
    elif a[:2] == ["pr", "list"] and "merged" in a:
        print((d / "merged").read_text() if (d / "merged").exists() else "")
    else:
        print((prs.read_text() if prs.exists() else "") if a[:2] == ["pr", "list"] else "main")
elif tool == "git":
    if a[2:4] == ["worktree", "add"]:
        pathlib.Path(a[-2]).mkdir(parents=True)
    elif a[2:4] == ["config", "core.hooksPath"]:
        sys.exit(1)
    elif a[2] == "ls-remote":
        print((d / "heads").read_text() if (d / "heads").exists() else "")
    elif a[2] == "rev-parse":
        print(d / a[-1].split("/")[-1])
elif a[:2] == ["tab", "create"]:
    print(json.dumps({"result": {"root_pane": {"pane_id": "%s"}}}))
elif a[:2] == ["tab", "list"]:
    labels = (d / "tabs").read_text().split() if (d / "tabs").exists() else []
    print(json.dumps({"result": {"tabs": [{"label": l, "tab_id": "w1:t" + str(i)} for i, l in enumerate(labels)]}}))
elif a[:2] == ["agent", "start"]:
    (d / "name").write_text(a[2])
    busy = d / "busy"
    n = int(busy.read_text()) if busy.exists() else 0
    if n:
        busy.write_text(str(n - 1))
        print(json.dumps({"error": {"code": "agent_pane_busy", "message": "not an available shell"}}))
        sys.exit(1)
    print(json.dumps({"error": {"code": "agent_not_ready"}} if blocked else {"result": {}}))
elif a[:2] == ["agent", "read"]:
    typed = (d / "typed").read_text() if (d / "typed").exists() else ""
    print("Quick safety check\n ❯ No, exit\n   Yes, I trust this folder" if blocked else "❯ " + typed)
elif a[:2] == ["agent", "send-keys"] and a[3:] == ["down", "enter"] and blocked:
    (d / "answered").touch()
elif a[:2] == ["agent", "send-keys"] and a[3:] == ["enter"] and (d / "typed").exists() and not (d / "dead").exists():
    (d / "typed").unlink()
    (d / "prompted").touch()
elif a[:2] == ["agent", "prompt"]:
    unsent = d / "unsent"
    if (d / "dead").exists() or unsent.exists():
        unsent.unlink(missing_ok=True)
        (d / "typed").write_text(a[3])
    else:
        (d / "prompted").touch()
elif a[:2] == ["agent", "list"]:
    status = "blocked" if blocked else "working" if (d / "prompted").exists() else "idle"
    print(json.dumps({"result": {"agents": [{"name": (d / "name").read_text() if (d / "name").exists() else "", "pane_id": "w9:p9", "agent_status": status, "interactive_ready": not blocked}]}}))
''' % PANE


class WorkerStart(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.repo = self.tmp / "repo"
        (self.repo / ".git").mkdir(parents=True)
        for tool in ("herdr", "git", "gh"):
            (self.tmp / tool).write_text(START_FAKE)
            (self.tmp / tool).chmod(0o755)

    def start(self, *extra, trust=True, topic="go-start", url=ISSUE, model="opus", effort="low", checkout=None, cwd=None):
        if trust:
            (self.tmp / "trust").touch()
        env = dict(os.environ, START_FAKE=str(self.tmp), PATH=f"{self.tmp}:{BIN}:{os.environ['PATH']}",
                   WORKER_START_TIMEOUT="3", WORKER_START_POLL="0.01")
        done = subprocess.run([sys.executable, str(BIN / "worker-start.py"), checkout or str(self.repo), topic, model, effort, url, *extra],
                              env=env, cwd=cwd, capture_output=True, text=True, timeout=30)
        log = self.tmp / "calls"
        calls = [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []
        return done, calls

    def test_relative_checkout_opens_the_tab_at_the_absolute_worktree(self):
        done, calls = self.start(checkout="repo", cwd=self.tmp)
        self.assertEqual(done.returncode, 0, done.stderr)
        tree = str(self.repo.resolve() / ".claude" / "worktrees" / "go-start-7-1")
        self.assertEqual([c[4] for c in calls if c[1:3] == ["tab", "create"]], [tree])

    def test_non_root_checkout_fails_naming_it_and_opens_no_tab(self):
        (self.repo / "sub").mkdir()
        (self.tmp / "plain").mkdir()
        for path in (str(self.repo / "sub"), str(self.tmp / "plain")):
            done, calls = self.start(checkout=path)
            self.assertEqual(done.returncode, 1, path)
            self.assertIn(path, done.stderr)
            self.assertFalse([c for c in calls if c[1:3] == ["tab", "create"]], path)

    def status(self):
        env = dict(os.environ, START_FAKE=str(self.tmp))
        out = subprocess.run([str(self.tmp / "herdr"), "agent", "list"], env=env, capture_output=True, text=True).stdout
        return json.loads(out)["result"]["agents"][0]["agent_status"]

    def test_trust_dialog_answered_yes_then_prompted_and_working(self):
        done, calls = self.start("--lead", "l")
        self.assertEqual(done.returncode, 0, done.stderr)
        tree = self.repo / ".claude" / "worktrees" / "go-start-7-1"
        self.assertEqual(done.stdout, f"go-start-7-1@{PANE} {tree}\n")
        keys = calls.index(["herdr", "agent", "send-keys", PANE, "down", "enter"])
        prompt = calls.index(["herdr", "agent", "prompt", PANE, f"/mumu-teamwork:kickoff work {ISSUE} lead l"])
        self.assertLess(keys, prompt, "prompted before the trust dialog was answered")
        self.assertEqual(self.status(), "working")
        self.assertIn(["git", "-C", str(self.repo), "worktree", "add", "-b", "go-start-7-1", str(tree), "origin/main"], calls)
        self.assertEqual(sorted(p.name for p in (self.tmp / "hooks").iterdir()), ["pre-commit"])

    def test_prompt_typed_but_unsent_is_sent_with_enter(self):
        (self.tmp / "unsent").touch()
        done, calls = self.start("--lead", "l", trust=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(done.stdout.startswith(f"go-start-7-1@{PANE} "), done.stdout)
        self.assertEqual(self.status(), "working")
        self.assertIn(["herdr", "agent", "send-keys", PANE, "enter"], calls)

    def test_prompt_never_delivered_fails_naming_the_pane(self):
        (self.tmp / "dead").touch()
        done, calls = self.start("--lead", "l", trust=False)
        self.assertEqual(done.returncode, 1)
        self.assertIn(f"herdr agent read {PANE}", done.stderr)
        self.assertEqual(done.stdout, "")
        sends = [c for c in calls if c[1:3] == ["agent", "prompt"] or c[1:3] == ["agent", "send-keys"] and c[4:] == ["enter"]]
        self.assertEqual(len(sends), 3, "one prompt and at most two resends")

    def test_tab_marks_the_session_a_worker(self):
        """The marker the lead monitors exit on (`scripts/team-watch.py`)."""
        _, calls = self.start(trust=False)
        tab = next(c for c in calls if c[1:3] == ["tab", "create"])
        self.assertIn("--env", tab)
        self.assertEqual(tab[tab.index("--env") + 1], "MUMU_ROLE=worker")

    def test_worktrees_excluded_once(self):
        (self.tmp / "exclude").write_text("# kept")
        self.start(trust=False)
        self.start(trust=False)
        self.assertEqual((self.tmp / "exclude").read_text(), "# kept\n/.claude/worktrees/\n")

    def test_no_dialog_sends_no_keys(self):
        done, calls = self.start(trust=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertFalse([c for c in calls if c[1:3] == ["agent", "send-keys"]])
        self.assertFalse([c for c in calls if c[1:3] == ["agent", "prompt"]])

    def test_continue_reuses_the_worktree_and_resumes(self):
        (self.repo / ".claude" / "worktrees" / "go-start-7-1").mkdir(parents=True)
        done, calls = self.start("--continue", trust=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertFalse([c for c in calls if c[0] == "git" and "worktree" in c])
        start = next(c for c in calls if c[1:3] == ["agent", "start"])
        self.assertEqual(start[start.index("--") + 1:], ["--name", "go-start-7-1", "--agent", "mumu-teamwork:worker", "--model", "opus", "--effort", "low", "--continue"])

    def test_session_never_ready_fails_naming_the_pane(self):
        (self.tmp / "herdr").write_text(START_FAKE.replace('and blocked:\n', 'and False:\n'))
        done, _ = self.start()
        self.assertEqual(done.returncode, 1)
        self.assertIn(f"herdr agent read {PANE}", done.stderr)

    def test_start_retried_while_pane_busy(self):
        (self.tmp / "busy").write_text("2")
        done, calls = self.start(trust=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len([c for c in calls if c[1:3] == ["agent", "start"]]), 3)

    def test_pane_always_busy_fails_naming_the_error(self):
        (self.tmp / "busy").write_text("100000")
        done, _ = self.start(trust=False)
        self.assertEqual(done.returncode, 1)
        self.assertIn("agent_pane_busy", done.stderr)

    def test_attempt_is_one_more_than_the_largest_found(self):
        """Issue 12 with remote branches `a-12-1` and `b-12-2` gets k=3; other issues' names never count; none found gives k=1."""
        url = "https://github.com/o/r/issues/12"
        done, _ = self.start(trust=False, topic="fix-login", url=url)
        self.assertTrue(done.stdout.startswith("fix-login-12-1@"), done.stdout + done.stderr)
        (self.tmp / "heads").write_text("s1\trefs/heads/a-12-1\ns2\trefs/heads/b-12-2\ns3\trefs/heads/c-112-9\ns4\trefs/heads/d-12\n")
        done, _ = self.start(trust=False, topic="fix-login", url=url)
        self.assertTrue(done.stdout.startswith("fix-login-12-3@"), done.stdout + done.stderr)
        (self.tmp / "prs").write_text("e-12-4\nf-13-8\n")
        done, _ = self.start(trust=False, topic="fix-login", url=url)
        self.assertTrue(done.stdout.startswith("fix-login-12-5@"), done.stdout + done.stderr)

    def test_local_worktree_counts_as_an_attempt(self):
        (self.repo / ".claude" / "worktrees" / "go-start-7-1").mkdir(parents=True)
        done, _ = self.start(trust=False)
        self.assertTrue(done.stdout.startswith("go-start-7-2@"), done.stdout + done.stderr)

    def test_new_attempt_refused_while_one_has_an_open_pr_or_a_live_tab(self):
        """`go-start-7-1` open as a pull request or a tab blocks `go-start-7-2`; other topics, tasks and closed pull requests do not."""
        for held, other in ((("open_prs", "go-start-7-1\n"), ("tabs", "other-7-1 go-start-8-1\n")),
                            (("tabs", "go-start-7-1\n"), ("open_prs", "other-7-3\nstart-17-1\n"))):
            with self.subTest(held=held):
                for f in ("open_prs", "tabs", "calls"):
                    (self.tmp / f).unlink(missing_ok=True)
                shutil.rmtree(self.repo / ".claude", ignore_errors=True)
                (self.tmp / other[0]).write_text(other[1])
                (self.tmp / "prs").write_text("go-start-7-1\n")
                done, calls = self.start(trust=False)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertTrue(done.stdout.startswith("go-start-7-2@"), done.stdout)
                (self.tmp / held[0]).write_text(held[1])
                (self.tmp / "calls").unlink()
                done, calls = self.start(trust=False)
                self.assertEqual(done.returncode, 1)
                self.assertIn("go-start-7-1", done.stderr)
                self.assertFalse([c for c in calls if c[1:3] == ["tab", "create"] or c[0] == "git" and "worktree" in c])

    def test_continue_is_exempt_from_the_open_attempt_refusal(self):
        (self.repo / ".claude" / "worktrees" / "go-start-7-1").mkdir(parents=True)
        (self.tmp / "open_prs").write_text("go-start-7-1\n")
        (self.tmp / "tabs").write_text("go-start-7-1\n")
        done, _ = self.start("--continue", trust=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(done.stdout.startswith("go-start-7-1@"), done.stdout)

    def test_continue_without_a_worktree_fails_before_the_tab(self):
        done, calls = self.start("--continue", trust=False)
        self.assertEqual(done.returncode, 1)
        self.assertIn("--continue", done.stderr)
        self.assertFalse([c for c in calls if c[0] == "herdr"])

    def test_topic_not_lowercase_words_refused_before_side_effects(self):
        for topic in ("Fix_Login", "fix--login", "", "fix", "one-two-three-four-five"):
            with self.subTest(topic=topic):
                done, calls = self.start(trust=False, topic=topic)
                self.assertEqual(done.returncode, 2)
                self.assertEqual(calls, [], "worktree or tab touched")
        self.assertFalse((self.repo / ".claude" / "worktrees").exists())

    def test_each_model_and_effort_starts_the_worker_on_them(self):
        """The lead's pick from kickoff's table reaches the worker's session as `--model <model> --effort <effort>` (#361)."""
        for model in ("opus", "sonnet"):
            for effort in ("low", "medium", "high"):
                with self.subTest(model=model, effort=effort):
                    done, calls = self.start(trust=False, model=model, effort=effort)
                    self.assertEqual(done.returncode, 0, done.stderr)
                    start = [c for c in calls if c[1:3] == ["agent", "start"]][-1]
                    self.assertEqual(start[start.index("--model"):start.index("--effort") + 2], ["--model", model, "--effort", effort])

    def test_another_model_or_effort_is_refused_before_side_effects(self):
        for model, effort in (("haiku", "low"), ("opus", "max"), ("sonnet", "xhigh"), ("low", "opus")):
            with self.subTest(model=model, effort=effort):
                done, calls = self.start(trust=False, model=model, effort=effort)
                self.assertEqual(done.returncode, 2)
                self.assertIn("invalid choice", done.stderr)
                self.assertEqual(calls, [], "worktree or tab touched")

    def test_no_owner_effort_flag(self):
        done, calls = self.start("--owner-effort", trust=False, effort="high")
        self.assertEqual(done.returncode, 2)
        self.assertIn("unrecognized arguments: --owner-effort", done.stderr)
        self.assertEqual(calls, [], "worktree or tab touched")

    def test_effort_labels_are_not_read(self):
        """A task labelled with no, another or several `effort:` labels starts at the effort given (#361)."""
        for labels in ([], [{"name": "effort:medium"}], [{"name": "effort:low"}, {"name": "effort:medium"}]):
            with self.subTest(labels=labels):
                (self.tmp / "issue").write_text(json.dumps({"state": "OPEN", "labels": labels, "body": ""}))
                done, calls = self.start(trust=False, model="sonnet", effort="high")
                self.assertEqual(done.returncode, 0, done.stderr)
                start = [c for c in calls if c[1:3] == ["agent", "start"]][-1]
                self.assertEqual(start[start.index("--effort") + 1], "high")

    def refused(self, why, **issue):
        """Start on a task the fake serves as `issue`, over an open one: refused naming `why`, before any worktree or tab."""
        task = {"state": "OPEN", "labels": [], "body": ""}
        task.update(issue)
        (self.tmp / "issue").write_text(json.dumps(task))
        done, calls = self.start(trust=False)
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn(why, done.stderr)
        self.assertFalse([c for c in calls if c[0] == "herdr" or c[:1] == ["git"] and "worktree" in c])
        self.assertFalse((self.repo / ".claude" / "worktrees").exists())

    def test_a_closed_task_starts_no_worker(self):
        self.refused("a stopped or finished task starts no worker", state="CLOSED")

    def test_a_backlog_issue_is_never_worked(self):
        self.refused("never worked", labels=[{"name": "backlog"}])

    def test_survey_starts_a_backlogs_survey_worker(self):
        """`--survey` starts a backlog's survey worker, prompted `survey`, on the model and effort given (#94)."""
        (self.tmp / "issue").write_text(json.dumps({"state": "OPEN", "labels": [{"name": "backlog"}], "body": "the owner's words"}))
        done, calls = self.start("--survey", "--lead", "l", effort="medium")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(done.stdout.startswith("go-start-7-1@"), done.stdout)
        self.assertIn(["herdr", "agent", "prompt", PANE, f"/mumu-teamwork:kickoff survey {ISSUE} lead l"], calls)

    def test_survey_of_a_task_is_refused(self):
        (self.tmp / "issue").write_text(json.dumps({"state": "OPEN", "labels": [], "body": ""}))
        done, calls = self.start("--survey", trust=False)
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("not labelled backlog", done.stderr)
        self.assertFalse([c for c in calls if c[0] == "herdr"])

    def test_an_open_blocker_holds_the_task(self):
        (self.tmp / "blockers").write_text(json.dumps([{"html_url": "https://github.com/o/r/issues/3", "state": "open"}]))
        self.refused("waits on https://github.com/o/r/issues/3")

    def test_a_closed_blocker_lets_it_start(self):
        (self.tmp / "blockers").write_text(json.dumps([{"html_url": "https://github.com/o/r/issues/3", "state": "closed"}]))
        done, _ = self.start(trust=False)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_share_starts_only_as_a_row_after_its_rows_merged(self):
        body = ("## Goal\nx\n\n## Shares\n\n| share | DoD | after | with |\n| --- | --- | --- | --- |\n"
                "| go-first | D1 | | go-start: interface agreed first |\n| go-start | D2 | go-first | |\n| go-side | D3 | | |\n")
        self.refused("its topic is a `## Shares` row", body=body.replace("go-start", "go-later"))
        self.refused("is after go-first", body=body)
        (self.tmp / "merged").write_text("go-first-8-1\ngo-first-7-1\n")
        (self.tmp / "issue").unlink()
        (self.tmp / "issue").write_text(json.dumps({"state": "OPEN", "labels": [], "body": body}))
        done, _ = self.start(trust=False)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_purely_sequential_split_starts_each_row_once_its_after_rows_merged(self):
        body = ("## Goal\nx\n\n## Shares\n\n| share | DoD | after | with |\n| --- | --- | --- | --- |\n"
                "| go-first | D1 | | |\n| go-start | D2 | go-first | |\n| go-last | D3 | go-start | |\n")
        self.refused("is after go-first", body=body)
        (self.tmp / "merged").write_text("go-first-7-1\n")
        (self.tmp / "issue").write_text(json.dumps({"state": "OPEN", "labels": [], "body": body}))
        done, _ = self.start(trust=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        done, _ = self.start(trust=False, topic="go-last")
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("is after go-start", done.stderr)

    def test_each_attempt_adds_its_worktree_on_its_own_branch(self):
        for k in (1, 2):
            done, calls = self.start(trust=False)
            self.assertEqual(done.returncode, 0, done.stderr)
        adds = [c[4:] for c in calls if c[3:5] == ["worktree", "add"]]
        trees = self.repo / ".claude" / "worktrees"
        self.assertEqual(adds, [["add", "-b", f"go-start-7-{k}", str(trees / f"go-start-7-{k}"), "origin/main"] for k in (1, 2)])


class Worktree(unittest.TestCase):
    """`worker-start.py`'s worktree step against real git: a new branch named after the worker, from the default branch."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.remote, self.repo = self.tmp / "remote.git", self.tmp / "repo"
        git(self.tmp, "init", "-q", "--bare", "-b", "main", str(self.remote))
        git(self.tmp, "clone", "-q", str(self.remote), str(self.repo))
        git(self.repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "base")
        git(self.repo, "push", "-q", "origin", "main")
        self.start = importlib.machinery.SourceFileLoader("worker_start", str(BIN / "worker-start.py")).load_module()
        self.start.repo_view = lambda field, repo: "main"

    def test_worktree_is_on_a_new_branch_named_after_the_worker_not_detached(self):
        base = git(self.repo, "rev-parse", "origin/main").strip()
        heads = {}
        for name in ("code-7-1", "report-8-1", "code-7-2"):
            tree = self.start.worktree(str(self.repo), name)
            self.assertEqual(git(tree, "branch", "--show-current").strip(), name)
            self.assertEqual(git(tree, "rev-parse", "HEAD").strip(), base)
            heads[name] = git(tree, "rev-parse", "--abbrev-ref", "HEAD").strip()
        self.assertEqual(len(set(heads.values())), 3, heads)


TASK = "https://github.com/o/main/issues/9"


class LeadStart(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.repo = self.tmp / "repo"
        (self.repo / ".git").mkdir(parents=True)
        for tool in ("herdr", "git", "gh"):
            (self.tmp / tool).write_text(START_FAKE)
            (self.tmp / tool).chmod(0o755)

    def start(self, *extra, checkout=None, cwd=None, pid=""):
        (self.tmp / "trust").touch()
        env = dict(os.environ, START_FAKE=str(self.tmp), PATH=f"{self.tmp}:{os.environ['PATH']}",
                   LEAD_START_TIMEOUT="3", LEAD_START_POLL="0.01", CLAUDE_PID=pid)
        done = subprocess.run([sys.executable, str(BIN / "lead-start.py"), checkout or str(self.repo), *extra],
                              env=env, cwd=cwd, capture_output=True, text=True, timeout=30)
        log = self.tmp / "calls"
        return done, [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []

    def claude_argv(self, calls):
        start = next(c for c in calls if c[1:3] == ["agent", "start"])
        return start[3], start[start.index("--") + 1:]

    def test_task_starts_the_lead_agent_and_prompts_see(self):
        done, calls = self.start(TASK)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, f"main-lead@{PANE}\n")
        self.assertEqual(self.claude_argv(calls), ("main-lead", ["--name", "main-lead", "--agent", "mumu-teamwork:lead", "--model", "opus", "--effort", "medium"]))
        self.assertIn(["herdr", "tab", "create", "--cwd", str(self.repo), "--label", "main-lead"], calls)
        keys = calls.index(["herdr", "agent", "send-keys", PANE, "down", "enter"])
        prompt = calls.index(["herdr", "agent", "prompt", PANE, f"/mumu-teamwork:kickoff see {TASK}"])
        self.assertLess(keys, prompt, "prompted before the trust dialog was answered")

    def test_repo_name_is_made_a_herdr_name(self):
        (self.tmp / "gh").write_text("#!/bin/sh\necho Kalaluthien.GitHub.io.and-a-long-tail\n")
        done, calls = self.start(TASK)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.claude_argv(calls)[0], "kalaluthien-github-io-lead")

    def test_no_task_prompts_resume(self):
        done, calls = self.start()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(["herdr", "agent", "prompt", PANE, "/mumu-teamwork:kickoff"], calls)

    def test_succeed_names_the_successor_next_and_keeps_given_flags(self):
        (self.tmp / "name").write_text("main-lead")
        done, calls = self.start("--succeed", "w9:p9", "--", "--model", "opus", "--effort", "high")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.claude_argv(calls), ("main-lead-next", ["--name", "main-lead", "--agent", "mumu-teamwork:lead", "--model", "opus", "--effort", "high"]))
        self.assertIn(["herdr", "agent", "prompt", PANE, "/mumu-teamwork:kickoff succeed w9:p9"], calls)

    def test_succeed_from_a_folder_lead_keeps_its_name(self):
        (self.tmp / "name").write_text("docs-lead")
        done, calls = self.start("--succeed", "w9:p9")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.claude_argv(calls)[0], "docs-lead-next")
        self.assertEqual(self.claude_argv(calls)[1][:2], ["--name", "docs-lead"])

    def test_succeed_without_flags_passes_on_the_originals_own(self):
        """Read from `ps` of `$CLAUDE_PID`: all but the program, `--continue`, `--resume`, `--name` and `--agent`."""
        (self.tmp / "name").write_text("main-lead")
        (self.tmp / "ps").write_text("#!/bin/sh\n[ \"$4\" = 123 ] && echo claude --name main-lead --agent mumu-teamwork:lead "
                                     "--resume abc --model opus --effort high --continue --permission-mode auto\n")
        (self.tmp / "ps").chmod(0o755)
        done, calls = self.start("--succeed", "w9:p9", pid="123")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.claude_argv(calls)[1], ["--name", "main-lead", "--agent", "mumu-teamwork:lead", "--model", "opus",
                                                      "--effort", "high", "--permission-mode", "auto"])

    def test_folder_names_a_folder_lead_with_no_task(self):
        done, calls = self.start("--folder", "mumu-paperwork")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, f"mumu-paperwork-lead@{PANE}\n")
        self.assertEqual(self.claude_argv(calls), ("mumu-paperwork-lead", ["--name", "mumu-paperwork-lead", "--agent", "mumu-teamwork:lead", "--model", "opus", "--effort", "medium"]))
        self.assertIn(["herdr", "tab", "create", "--cwd", str(self.repo), "--label", "mumu-paperwork-lead"], calls)
        self.assertIn(["herdr", "agent", "prompt", PANE, "/mumu-teamwork:kickoff"], calls)

    def test_folder_with_a_task_prompts_see(self):
        done, calls = self.start(TASK, "--folder", "docs")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.claude_argv(calls)[0], "docs-lead")
        self.assertIn(["herdr", "agent", "prompt", PANE, f"/mumu-teamwork:kickoff see {TASK}"], calls)

    def test_live_folder_lead_refuses_a_second(self):
        (self.tmp / "name").write_text("docs-lead")
        done, calls = self.start("--folder", "docs")
        self.assertEqual(done.returncode, 1)
        self.assertIn("docs-lead is already live", done.stderr)

    def test_live_lead_refuses_a_second(self):
        (self.tmp / "name").write_text("main-lead")
        done, calls = self.start(TASK)
        self.assertEqual(done.returncode, 1)
        self.assertIn("already live", done.stderr)
        self.assertFalse([c for c in calls if c[1:3] in (["tab", "create"], ["agent", "start"])])

    def test_relative_checkout_opens_the_tab_at_its_absolute_root(self):
        done, calls = self.start(TASK, checkout="repo", cwd=self.tmp)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(["herdr", "tab", "create", "--cwd", str(self.repo.resolve()), "--label", "main-lead"], calls)

    def test_non_root_checkout_fails_naming_it_and_opens_no_tab(self):
        (self.repo / "sub").mkdir()
        (self.tmp / "plain").mkdir()
        for path in (str(self.repo / "sub"), str(self.tmp / "plain")):
            done, calls = self.start(TASK, checkout=path)
            self.assertEqual(done.returncode, 1, path)
            self.assertIn(path, done.stderr)
            self.assertFalse([c for c in calls if c[1:3] == ["tab", "create"]], path)

    def test_bad_arguments_start_nothing(self):
        for extra in (["--succeed"], ["--continue"], [TASK, TASK], ["--folder"], ["--succeed", "w9:p9", "--folder", "docs"]):
            done, calls = self.start(*extra)
            self.assertEqual(done.returncode, 2, extra)
            self.assertFalse(calls, extra)


class LeadName(unittest.TestCase):
    def name(self, labels, folders=(), args=(ISSUE,)):
        tmp = pathlib.Path(tempfile.mkdtemp()).resolve()
        for f in folders:
            (tmp / f).mkdir()
        (tmp / "gh").write_text("#!/bin/sh\nif [ \"$1\" = issue ]; then echo '%s'; else echo Mumu.Plugin; fi\n"
                                % json.dumps({"labels": [{"name": l} for l in labels]}))
        (tmp / "gh").chmod(0o755)
        env = dict(os.environ, PATH=f"{tmp}:{os.environ['PATH']}")
        done = subprocess.run([sys.executable, str(BIN / "lead-name.py"), *args], cwd=tmp, env=env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.strip()

    def test_a_scoped_task_names_its_folder_lead(self):
        self.assertEqual(self.name(["effort:low", "scope:docs"], ["docs"]), "docs-lead")

    def test_otherwise_the_repository_lead(self):
        self.assertEqual(self.name(["effort:low"]), "mumu-plugin-lead")
        self.assertEqual(self.name(["scope:docs"]), "mumu-plugin-lead")
        self.assertEqual(self.name([], args=()), "mumu-plugin-lead")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, text=True).stdout


# The hook ../scripts/sync.sh (workspace repo) writes as pre-commit and pre-push.
WRAPPER = """#!/bin/sh
guard="%s"
hook=$(basename "$0")
in=$(mktemp) || exit 1
trap 'rm -f "$in"' EXIT
cat >| "$in"
GUARD="$guard" sh -c '. "$GUARD"' "$hook" "$@" < "$in" || exit 1
[ -f "hooks/$hook" ] || exit 0
"hooks/$hook" "$@" < "$in"
""" % (BIN / "default-branch-guard.sh")


class DefaultBranchGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.remote, self.repo = self.tmp / "remote.git", self.tmp / "repo"
        git(self.tmp, "init", "-q", "--bare", "-b", "main", str(self.remote))
        git(self.tmp, "init", "-q", "-b", "main", str(self.repo))
        git(self.repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "base")
        git(self.repo, "push", "-q", str(self.remote), "main", "main:topic")
        for hook in ("pre-commit", "pre-push"):
            path = self.repo / ".git" / "hooks" / hook
            path.write_text(WRAPPER)
            path.chmod(0o755)

    def test_a_push_deleting_a_branch_from_the_default_branch_passes(self):
        out = subprocess.run(["git", "push", str(self.remote), "--delete", "topic"], cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        branches = subprocess.run(["git", "-C", self.remote, "branch", "--list"], capture_output=True, text=True, check=True).stdout
        self.assertEqual(branches.split(), ["*", "main"])

    def test_a_commit_on_the_default_branch_is_refused(self):
        out = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "--allow-empty", "-m", "x"],
                             cwd=self.repo, capture_output=True, text=True)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn('the default branch "main" is refused', out.stderr)


SCOPE = BIN / "check-scope.py"
# A mapping and the tree it reads: skills need the evals, a script its test, a test itself, a note nothing.
FIXTURE = {"every": ["judge", "*/tests/test_*.py", "*/evals/*"],
           "rules": [{"paths": ["p/skills/**"], "checks": ["judge", "p/evals/*"]},
                     {"paths": ["p/bin/*.py"], "checks": ["judge", "p/tests/test_bin.py"]},
                     {"paths": ["p/tests/test_*.py"], "checks": ["judge", "p/tests/test_{0}.py"]},
                     {"paths": ["p/notes/**"], "checks": []}]}
FIXTURE_TREE = ["checks.json", "p", "p/bin", "p/bin/x.py", "p/tests", "p/tests/test_bin.py", "p/tests/test_hooks.py", "p/evals",
                "p/evals/a", "p/evals/a/prompt.md", "p/evals/b", "p/evals/b/prompt.md", "p/skills", "p/skills/s", "p/skills/s/SKILL.md",
                "p/notes", "p/notes/n.md"]
EVERY = ["p/evals/a", "p/evals/b", "p/tests/test_bin.py", "p/tests/test_hooks.py"]


def passed(sha, *checks):
    return f"PASSED: {sha}\n" + "".join(f"- {c}\n" for c in checks)


def scoped(comments, files, **pr):
    """`merge` on a PR changing `files` under the fixture mapping."""
    return merge(comments, files=files, mapping=FIXTURE, tree=FIXTURE_TREE, **pr)


class MergeScope(unittest.TestCase):
    """pr-merge.py requires a pass of each check the scope needs, and of no other."""

    def test_a_check_the_scope_needs_without_a_pass_refuses(self):
        result, words = scoped([f"APPROVED: {HEAD}"], ["p/bin/x.py"])
        self.assertIsNone(words)
        self.assertIn("`p/tests/test_bin.py` has no pass", result.stderr)
        self.assertIn(f"PASSED: {HEAD}", result.stderr)
        for other in ("test_hooks", "p/evals/"):
            self.assertNotIn(other, result.stderr)

    def test_the_checks_the_scope_leaves_out_are_not_asked(self):
        result, words = scoped([f"APPROVED: {HEAD}", passed(HEAD, "p/tests/test_bin.py")], ["p/bin/x.py"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(words[-1], HEAD)
        result, words = scoped([], ["p/notes/n.md"])
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_the_judge_is_asked_when_the_scope_names_it(self):
        result, words = scoped([passed(HEAD, "p/tests/test_bin.py")], ["p/bin/x.py"])
        self.assertIsNone(words)
        self.assertIn("launch the judge", result.stderr)

    def test_a_change_to_the_mapping_or_an_unmapped_path_needs_every_check(self):
        for files in (["checks.json"], ["p/notes/n.md", "checks.json"], ["p/other.txt"]):
            with self.subTest(files=files):
                result, words = scoped([passed(HEAD, "p/tests/test_bin.py")], files)
                self.assertIsNone(words)
                for check in EVERY[:2] + EVERY[3:]:
                    self.assertIn(f"`{check}` has no pass", result.stderr)
                self.assertNotIn("`p/tests/test_bin.py` has no pass", result.stderr)
                self.assertIn("launch the judge", result.stderr)
                result, words = scoped([f"APPROVED: {HEAD}", passed(HEAD, *EVERY)], files)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_record_names_its_checks_on_the_lines_after_it(self):
        for record in (f"PASSED: {HEAD}\np/tests/test_bin.py", f"passed {HEAD}\n- `p/tests/test_bin.py`"):
            with self.subTest(record=record):
                result, words = scoped([f"APPROVED: {HEAD}", record], ["p/bin/x.py"])
                self.assertEqual(result.returncode, 0, result.stderr)
        for record in (f"PASSED: {OLD}\np/tests/test_bin.py", f"PASSED: {HEAD} p/tests/test_bin.py", f"see PASSED: {HEAD}\np/tests/test_bin.py"):
            with self.subTest(record=record):
                result, words = scoped([f"APPROVED: {HEAD}", record], ["p/bin/x.py"])
                self.assertIsNone(words)

    def test_a_small_change_naming_no_task_merges_without_the_judge(self):
        """A body naming no task with at most 30 changed lines, in any number of files, needs every check of its scope but the judge."""
        small = [{"filename": "p/bin/x.py", "additions": 10, "deletions": 5}, {"filename": "p/skills/s/SKILL.md", "additions": 15}]
        result, words = scoped([passed(HEAD, "p/tests/test_bin.py", "p/evals/a", "p/evals/b")], small, body="Fix x: see line 3")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(words[-1], HEAD)

    def test_a_small_change_naming_no_task_still_needs_its_test_checks(self):
        result, words = scoped([passed(HEAD, "p/evals/a", "p/evals/b")], [{"filename": "p/bin/x.py", "additions": 30}], body="")
        self.assertIsNone(words)
        self.assertIn("`p/tests/test_bin.py` has no pass", result.stderr)
        self.assertNotIn("judge", result.stderr)

    def test_a_change_naming_no_task_at_31_lines_is_refused(self):
        big = [{"filename": "p/bin/x.py", "additions": 16}, {"filename": "p/notes/n.md", "additions": 10, "deletions": 5}]
        result, words = scoped([f"APPROVED: {HEAD}", passed(HEAD, "p/tests/test_bin.py")], big, body="")
        self.assertIsNone(words)
        self.assertIn("names no task, and its 31 changed lines exceed a small change's 30", result.stderr)

    def test_a_repository_without_the_mapping_needs_only_the_judge(self):
        result, words = merge([f"APPROVED: {HEAD}"], files=["p/bin/x.py", "checks.json"])
        self.assertEqual(result.returncode, 0, result.stderr)


class MergeScopeCarry(unittest.TestCase):
    """A pass at an earlier commit carries to the head while the commits since change none of its check's paths."""

    def test_a_pass_carries_across_commits_outside_its_paths(self):
        for since in (["p/notes/n.md"], []):
            with self.subTest(since=since):
                result, words = scoped([f"APPROVED: {OLD}", passed(OLD, "p/tests/test_bin.py")], ["p/bin/x.py"], since={OLD: since})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(words[-1], HEAD)
        result, words = scoped([f"APPROVED: {HEAD}", passed(OLD, "p/tests/test_bin.py")], ["p/bin/x.py", "p/skills/s/SKILL.md"],
                               since={OLD: ["p/skills/s/SKILL.md"]}, **{})
        self.assertIn("`p/evals/a` has no pass", result.stderr)
        self.assertNotIn("test_bin", result.stderr)

    def test_the_judge_is_asked_again_after_a_commit_inside_its_paths(self):
        result, words = scoped([f"APPROVED: {OLD}", passed(HEAD, "p/tests/test_bin.py")], ["p/bin/x.py"], since={OLD: ["p/bin/x.py"]})
        self.assertIsNone(words)
        self.assertIn(f"`APPROVED: {OLD}` does not carry", result.stderr)
        self.assertIn("resume the judge", result.stderr)

    def test_a_commit_inside_its_paths_names_only_that_check_to_rerun(self):
        result, words = scoped([f"APPROVED: {HEAD}", passed(OLD, "p/tests/test_bin.py", "p/tests/test_hooks.py")],
                               ["p/bin/x.py", "p/tests/test_hooks.py"], since={OLD: ["p/tests/test_hooks.py"]})
        self.assertIsNone(words)
        self.assertIn(f"`p/tests/test_hooks.py` has no pass at the head {HEAD} and the commits since {OLD}", result.stderr)
        self.assertNotIn("test_bin", result.stderr)

    def test_a_commit_editing_the_mapping_reruns_every_check(self):
        result, words = scoped([f"APPROVED: {OLD}", passed(OLD, "p/tests/test_bin.py")], ["p/bin/x.py"], since={OLD: ["checks.json"]})
        self.assertIsNone(words)
        self.assertIn("`p/tests/test_bin.py` has no pass", result.stderr)
        self.assertIn(f"`APPROVED: {OLD}` does not carry", result.stderr)

    def test_a_pass_at_no_ancestor_of_the_head_does_not_carry(self):
        result, words = scoped([f"APPROVED: {HEAD}", passed(OLD, "p/tests/test_bin.py")], ["p/bin/x.py"])
        self.assertIsNone(words)
        self.assertIn("`p/tests/test_bin.py` has no pass", result.stderr)

    def test_a_behind_refusal_names_only_the_checks_the_base_touches(self):
        cases = {"p/skills/s/SKILL.md": [], "p/bin/y.py": ["p/tests/test_bin.py"], "checks.json": ["p/tests/test_bin.py"]}
        for moved, rerun in cases.items():
            with self.subTest(moved=moved):
                result, words = scoped([f"APPROVED: {HEAD}", passed(HEAD, "p/tests/test_bin.py")], ["p/bin/x.py"], behind=2, base_files=[moved])
                self.assertIsNone(words)
                if rerun:
                    self.assertIn(f"these checks cover: {', '.join(rerun)}; merge it in, rerun only those", result.stderr)
                else:
                    self.assertIn("no rerun needed", result.stderr)


def tree_names(root):
    """Each tracked file of `root` and each folder above one."""
    files = subprocess.run(["git", "-C", root, "ls-files"], capture_output=True, text=True, check=True).stdout.split()
    return sorted({str(parent) for f in files for parent in [pathlib.PurePosixPath(f), *pathlib.PurePosixPath(f).parents][:-1]})


REPO = ROOT.parent


class CheckScope(unittest.TestCase):
    """check-scope.py prints what this repository's checks.json assigns to a PR's changed paths."""

    @classmethod
    def setUpClass(cls):
        cls.mapping = json.loads((REPO / "checks.json").read_text())
        cls.tree = tree_names(REPO)
        cls.every = sorted(c for c in cls.tree if any(re.fullmatch(pattern(g), c) for g in cls.mapping["every"] if g != "judge"))

    def scope(self, files, mapping=True, lines=0):
        tmp = pathlib.Path(tempfile.mkdtemp())
        pr = {"headRefOid": HEAD, "baseRefName": "main", "tree": self.tree, "files": [{"filename": f, "additions": lines} for f in files]}
        if mapping:
            pr["mapping"] = self.mapping
        (tmp / "pr.json").write_text(json.dumps(pr))
        (tmp / "gh").write_text(MERGE_GH)
        (tmp / "gh").chmod(0o755)
        env = dict(os.environ, PATH=f"{tmp}:{os.environ['PATH']}")
        done = subprocess.run([sys.executable, str(SCOPE), PR_URL], capture_output=True, text=True, env=env, cwd=tmp)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.splitlines()

    def test_the_every_set_is_every_test_file_and_eval_case(self):
        self.assertEqual(self.every, sorted(c for c in self.tree if re.fullmatch(r"[^/]+/tests/test_[^/]+\.py|[^/]+/evals/[^/]+", c)))
        self.assertGreater(len(self.every), 50)

    def test_a_rules_file_change_needs_the_judge_and_its_plugins_evals_only(self):
        printed = self.scope(["mumu-teamwork/skills/kickoff/references/worker-playbook.md"])
        self.assertTrue(printed[0].startswith("judge: "))
        self.assertTrue(all(c.startswith("mumu-teamwork/") for c in printed[1:]))
        self.assertIn("mumu-teamwork/evals/work", printed)
        self.assertLess(len(printed), len(self.every) // 2)

    def test_a_script_change_needs_its_tests_and_no_eval(self):
        printed = self.scope(["mumu-teamwork/bin/pr-merge.py"])
        self.assertIn("mumu-teamwork/tests/test_bin.py", printed)
        self.assertFalse([c for c in printed if "/evals/" in c])
        self.assertFalse([c for c in printed if not c.startswith(("judge: ", "mumu-teamwork/"))])

    def test_a_hook_change_needs_the_hook_tests(self):
        printed = self.scope(["mumu-teamwork/scripts/bash-guard.py"])
        self.assertIn("mumu-teamwork/tests/test_scripts.py", printed)
        self.assertFalse([c for c in printed if not c.startswith(("judge: ", "mumu-teamwork/"))])

    def test_an_unmapped_path_or_the_mapping_itself_needs_the_full_set(self):
        for files in (["no-such-folder/x.txt"], ["checks.json"], []):
            with self.subTest(files=files):
                printed = self.scope(files)
                self.assertEqual(printed[0], "judge: sonnet")
                self.assertEqual(printed[1:], self.every)

    def test_the_judge_runs_on_sonnet_at_any_size(self):
        """A pull request's judge is Sonnet at any size, where main put Opus above 20 changed lines (#361)."""
        for lines in (20, 21, 500):
            with self.subTest(lines=lines):
                self.assertEqual(self.scope(["no-such-folder/x.txt"], lines=lines)[0], "judge: sonnet")

    def test_a_repository_without_the_mapping_needs_the_judge_alone(self):
        self.assertEqual(self.scope(["mumu-teamwork/bin/pr-merge.py"], mapping=False), ["judge: sonnet"])

if __name__ == "__main__":
    unittest.main()

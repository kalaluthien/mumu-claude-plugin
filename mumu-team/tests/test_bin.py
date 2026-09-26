"""The `bin/` commands, each run against fake `herdr`, `git` and `gh` commands on PATH that log every call.

Run: python3 -m unittest discover mumu-team/tests
"""
import importlib.machinery
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

BIN = pathlib.Path(__file__).resolve().parent.parent / "bin"
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
        done = subprocess.run([sys.executable, str(BIN / "decide.py"), ISSUE_URL, *args], input=text, env=env,
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


MERGE = pathlib.Path(__file__).resolve().parent.parent / "bin" / "merge.py"
PR_URL = "https://github.com/o/r/pull/1"
HEAD, OLD = "a" * 40, "b" * 40

# `gh pr view` serves pr.json; `gh pr merge` logs its words and, like GitHub, refuses a pin that is not the head,
# read from `head` when present, so a test can move the head between the view and the merge.
MERGE_GH = r'''#!/usr/bin/env python3
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


def merge(comments, moved_to=None, reviews=(), url=PR_URL):
    """Run merge.py on a PR at HEAD holding `comments`; `moved_to` moves the head once it is read. Return (result, merge words or None)."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    pr = {"headRefOid": HEAD, "comments": [{"body": b} for b in comments], "reviews": [{"body": b} for b in reviews]}
    (tmp / "pr.json").write_text(json.dumps(pr))
    if moved_to:
        (tmp / "head").write_text(moved_to)
    (tmp / "gh").write_text(MERGE_GH)
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
    agent = {"name": "close-7", "pane_id": "w1:p7", "tab_id": "w1:t7", "agent_status": "idle"}
    agents = [agent] if alive.exists() else []
    print(json.dumps({"result": {"agents": agents}}))
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
        done = subprocess.run([sys.executable, str(BIN / "worker-close.py"), "close-7"],
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
    print((d / "prs").read_text() if a[:2] == ["pr", "list"] and (d / "prs").exists() else "" if a[:2] == ["pr", "list"] else "main")
elif tool == "git":
    if a[2:4] == ["worktree", "add"]:
        pathlib.Path(a[5]).mkdir(parents=True)
    elif a[2:4] == ["config", "core.hooksPath"]:
        sys.exit(1)
    elif a[2] == "ls-remote":
        print((d / "heads").read_text() if (d / "heads").exists() else "")
    elif a[2] == "rev-parse":
        print(d / a[-1].split("/")[-1])
elif a[:2] == ["tab", "create"]:
    print(json.dumps({"result": {"root_pane": {"pane_id": "%s"}}}))
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
    print("Quick safety check\n ❯ No, exit\n   Yes, I trust this folder" if blocked else "❯")
elif a[:2] == ["agent", "send-keys"] and a[3:] == ["down", "enter"] and blocked:
    (d / "answered").touch()
elif a[:2] == ["agent", "prompt"]:
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

    def start(self, *extra, trust=True, topic="start", url=ISSUE, effort="low", checkout=None, cwd=None):
        if trust:
            (self.tmp / "trust").touch()
        env = dict(os.environ, START_FAKE=str(self.tmp), PATH=f"{self.tmp}:{BIN}:{os.environ['PATH']}",
                   WORKER_START_TIMEOUT="3", WORKER_START_POLL="0.01")
        done = subprocess.run([sys.executable, str(BIN / "worker-start.py"), checkout or str(self.repo), topic, effort, url, *extra],
                              env=env, cwd=cwd, capture_output=True, text=True, timeout=30)
        log = self.tmp / "calls"
        calls = [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []
        return done, calls

    def test_relative_checkout_opens_the_tab_at_the_absolute_worktree(self):
        done, calls = self.start(checkout="repo", cwd=self.tmp)
        self.assertEqual(done.returncode, 0, done.stderr)
        tree = str(self.repo.resolve() / ".claude" / "worktrees" / "start-7-1")
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
        done, calls = self.start("--leader", "l")
        self.assertEqual(done.returncode, 0, done.stderr)
        tree = self.repo / ".claude" / "worktrees" / "start-7-1"
        self.assertEqual(done.stdout, f"start-7-1@{PANE} {tree}\n")
        keys = calls.index(["herdr", "agent", "send-keys", PANE, "down", "enter"])
        prompt = calls.index(["herdr", "agent", "prompt", PANE, f"/mumu-team:kickoff work {ISSUE} leader l"])
        self.assertLess(keys, prompt, "prompted before the trust dialog was answered")
        self.assertEqual(self.status(), "working")
        self.assertIn(["git", "-C", str(self.repo), "worktree", "add", "--detach", str(tree), "origin/main"], calls)
        self.assertTrue((self.tmp / "hooks" / "pre-commit").exists() and (self.tmp / "hooks" / "pre-push").exists())

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
        (self.repo / ".claude" / "worktrees" / "start-7-1").mkdir(parents=True)
        done, calls = self.start("--continue", trust=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertFalse([c for c in calls if c[0] == "git" and "worktree" in c])
        start = next(c for c in calls if c[1:3] == ["agent", "start"])
        self.assertEqual(start[start.index("--") + 1:], ["--name", "start-7-1", "--agent", "mumu-team:worker", "--model", "opus", "--effort", "low", "--continue"])

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
        (self.repo / ".claude" / "worktrees" / "start-7-1").mkdir(parents=True)
        done, _ = self.start(trust=False)
        self.assertTrue(done.stdout.startswith("start-7-2@"), done.stdout + done.stderr)

    def test_continue_without_a_worktree_fails_before_the_tab(self):
        done, calls = self.start("--continue", trust=False)
        self.assertEqual(done.returncode, 1)
        self.assertIn("--continue", done.stderr)
        self.assertFalse([c for c in calls if c[0] == "herdr"])

    def test_topic_not_lowercase_words_refused_before_side_effects(self):
        for topic in ("Fix_Login", "fix--login", ""):
            with self.subTest(topic=topic):
                done, calls = self.start(trust=False, topic=topic)
                self.assertEqual(done.returncode, 2)
                self.assertEqual(calls, [], "worktree or tab touched")
        self.assertFalse((self.repo / ".claude" / "worktrees").exists())

    def test_high_effort_refused_before_side_effects(self):
        done, calls = self.start(trust=False, effort="high")
        self.assertEqual(done.returncode, 2)
        self.assertIn("--owner-effort", done.stderr)
        self.assertEqual(len(done.stderr.strip().splitlines()), 1)
        self.assertEqual(calls, [], "worktree or tab touched")

    def test_high_effort_with_owner_flag_starts_at_high(self):
        done, calls = self.start("--owner-effort", trust=False, effort="high")
        self.assertEqual(done.returncode, 0, done.stderr)
        start = next(c for c in calls if c[1:3] == ["agent", "start"])
        self.assertEqual(start[start.index("--effort") + 1], "high")

    def test_low_and_medium_start(self):
        for effort in ("low", "medium"):
            with self.subTest(effort=effort):
                done, calls = self.start(trust=False, effort=effort)
                self.assertEqual(done.returncode, 0, done.stderr)
                start = [c for c in calls if c[1:3] == ["agent", "start"]][-1]
                self.assertEqual(start[start.index("--effort") + 1], effort)


GOAL = "https://github.com/o/main/issues/9"


class LeadStart(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.repo = self.tmp / "repo"
        (self.repo / ".git").mkdir(parents=True)
        for tool in ("herdr", "git", "gh"):
            (self.tmp / tool).write_text(START_FAKE)
            (self.tmp / tool).chmod(0o755)

    def start(self, *extra, checkout=None, cwd=None):
        (self.tmp / "trust").touch()
        env = dict(os.environ, START_FAKE=str(self.tmp), PATH=f"{self.tmp}:{os.environ['PATH']}",
                   LEAD_START_TIMEOUT="3", LEAD_START_POLL="0.01")
        done = subprocess.run([sys.executable, str(BIN / "lead-start.py"), checkout or str(self.repo), *extra],
                              env=env, cwd=cwd, capture_output=True, text=True, timeout=30)
        log = self.tmp / "calls"
        return done, [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []

    def claude_argv(self, calls):
        start = next(c for c in calls if c[1:3] == ["agent", "start"])
        return start[3], start[start.index("--") + 1:]

    def test_goal_starts_the_lead_agent_and_prompts_see(self):
        done, calls = self.start(GOAL)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, f"main-lead@{PANE}\n")
        self.assertEqual(self.claude_argv(calls), ("main-lead", ["--name", "main-lead", "--agent", "mumu-team:lead", "--model", "opus", "--effort", "medium"]))
        self.assertIn(["herdr", "tab", "create", "--cwd", str(self.repo), "--label", "main-lead"], calls)
        keys = calls.index(["herdr", "agent", "send-keys", PANE, "down", "enter"])
        prompt = calls.index(["herdr", "agent", "prompt", PANE, f"/mumu-team:kickoff see {GOAL}"])
        self.assertLess(keys, prompt, "prompted before the trust dialog was answered")

    def test_repo_name_is_made_a_herdr_name(self):
        (self.tmp / "gh").write_text("#!/bin/sh\necho Kalaluthien.GitHub.io.and-a-long-tail\n")
        done, calls = self.start(GOAL)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.claude_argv(calls)[0], "kalaluthien-github-io-lead")

    def test_no_goal_prompts_resume(self):
        done, calls = self.start()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(["herdr", "agent", "prompt", PANE, "/mumu-team:kickoff"], calls)

    def test_succeed_names_the_successor_next_and_keeps_given_flags(self):
        (self.tmp / "name").write_text("main-lead")
        done, calls = self.start("--succeed", "w9:p9", "--", "--model", "opus", "--effort", "high")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.claude_argv(calls), ("main-lead-next", ["--name", "main-lead", "--agent", "mumu-team:lead", "--model", "opus", "--effort", "high"]))
        self.assertIn(["herdr", "agent", "prompt", PANE, "/mumu-team:kickoff succeed w9:p9"], calls)

    def test_succeed_from_a_folder_lead_keeps_its_name(self):
        (self.tmp / "name").write_text("docs-lead")
        done, calls = self.start("--succeed", "w9:p9")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.claude_argv(calls)[0], "docs-lead-next")
        self.assertEqual(self.claude_argv(calls)[1][:2], ["--name", "docs-lead"])

    def test_live_lead_refuses_a_second(self):
        (self.tmp / "name").write_text("main-lead")
        done, calls = self.start(GOAL)
        self.assertEqual(done.returncode, 1)
        self.assertIn("already live", done.stderr)
        self.assertFalse([c for c in calls if c[1:3] in (["tab", "create"], ["agent", "start"])])

    def test_relative_checkout_opens_the_tab_at_its_absolute_root(self):
        done, calls = self.start(GOAL, checkout="repo", cwd=self.tmp)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(["herdr", "tab", "create", "--cwd", str(self.repo.resolve()), "--label", "main-lead"], calls)

    def test_non_root_checkout_fails_naming_it_and_opens_no_tab(self):
        (self.repo / "sub").mkdir()
        (self.tmp / "plain").mkdir()
        for path in (str(self.repo / "sub"), str(self.tmp / "plain")):
            done, calls = self.start(GOAL, checkout=path)
            self.assertEqual(done.returncode, 1, path)
            self.assertIn(path, done.stderr)
            self.assertFalse([c for c in calls if c[1:3] == ["tab", "create"]], path)

    def test_bad_arguments_start_nothing(self):
        for extra in (["--succeed"], ["--continue"], [GOAL, GOAL]):
            done, calls = self.start(*extra)
            self.assertEqual(done.returncode, 2, extra)
            self.assertFalse(calls, extra)


REVIEW = importlib.machinery.SourceFileLoader("review_model", str(BIN / "review-model.py")).load_module()


def git(repo, *args):
    subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True)


class ReviewModel(unittest.TestCase):
    def test_twenty_changed_lines_get_sonnet_and_twenty_one_get_opus(self):
        with tempfile.TemporaryDirectory() as repo:
            git(repo, "init", "-q", "-b", "main")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "base")
            git(repo, "checkout", "-q", "-b", "topic")
            path = pathlib.Path(repo, "f.txt")
            printed = []
            for n in (20, 21):
                path.write_text("".join(f"{i}\n" for i in range(n)))
                git(repo, "add", "f.txt")
                git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", str(n))
                out = subprocess.run([str(BIN / "review-model.py"), "main", "HEAD"], cwd=repo, capture_output=True, text=True, check=True)
                printed.append(out.stdout.strip())
                git(repo, "reset", "-q", "--hard", "main")
            self.assertEqual(printed, ["sonnet (20 changed lines)", "opus (21 changed lines)"])

    def test_insertions_and_deletions_both_count(self):
        self.assertEqual(REVIEW.changed(" 2 files changed, 10 insertions(+), 2 deletions(-)"), 12)
        self.assertEqual(REVIEW.changed(" 1 file changed, 1 deletion(-)"), 1)
        self.assertEqual(REVIEW.changed(""), 0)


if __name__ == "__main__":
    unittest.main()

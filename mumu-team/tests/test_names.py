"""`lib/names.py`: worker and lead names, the checkout's root and its workers' worktrees.

Run: python3 -m unittest discover mumu-team/tests
"""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
import names  # noqa: E402


class Names(unittest.TestCase):
    def test_worker_round_trips_its_attempt(self):
        self.assertEqual(names.worker("fold-rest", 22, 3), "fold-rest-22-3")
        self.assertEqual(names.attempt("fold-rest-22-3"), 3)
        self.assertEqual(names.attempt("fold-rest-22-3", n=22), 3)
        self.assertEqual(names.attempt("fold-rest-22-3", "fold-rest", 22), 3)

    def test_attempt_refuses_other_names_tasks_and_topics(self):
        for name, topic, n in [("mumu-lead", None, None), ("Fold-22-1", None, None), ("fold-22", None, None),
                               ("fold-22-1", None, 2), ("fold-22-1", "rest", 22), (None, None, None)]:
            with self.subTest(name=name, topic=topic, n=n):
                self.assertIsNone(names.attempt(name, topic, n))

    def test_lead_is_cut_so_its_successor_fits_herdr(self):
        self.assertEqual(names.lead("mumu-claude-plugin"), "mumu-claude-plugin-lead")
        self.assertEqual(names.lead("My Repo.v2"), "my-repo-v2-lead")
        self.assertLessEqual(len(names.lead("x" * 40) + "-next"), 32)

    def test_checkout_is_a_root_holding_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertRaises(RuntimeError, names.checkout, tmp)
            (pathlib.Path(tmp) / ".git").mkdir()
            self.assertEqual(names.checkout(tmp), pathlib.Path(tmp).resolve())

    def test_workers_are_named_workers_under_the_checkouts_worktrees(self):
        root = names.worktrees("/w/plugins")
        listed = [
            {"name": "fold-rest-22-1", "cwd": str(root / "fold-rest-22-1"), "agent_status": "working"},
            {"name": "plugins-lead", "cwd": "/w/plugins", "agent_status": "idle"},
            {"name": "other-5-1", "cwd": "/w/other/.claude/worktrees/other-5-1"},
            {"name": "sib-6-1", "cwd": "/w/plugins-2/.claude/worktrees/sib-6-1"},
            {"name": "no-cwd-7-1"},
        ]
        self.assertEqual(names.workers(listed, "/w/plugins"), {"fold-rest-22-1": "working"})


if __name__ == "__main__":
    unittest.main()

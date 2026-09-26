"""`tab-sweep.py` run against a fake herdr that serves a pane and agent list and logs every call.

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
CHECKOUT = "/w/plugins"
WT = CHECKOUT + "/.claude/worktrees"

FAKE = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
d, a = pathlib.Path(os.environ["FAKE"]), sys.argv[1:]
with open(d / "calls", "a") as f:
    f.write(json.dumps(a) + "\n")
if a[:2] == ["pane", "list"]:
    print(json.dumps({"result": {"panes": json.loads((d / "panes").read_text())}}))
elif a[:2] == ["agent", "list"]:
    print(json.dumps({"result": {"agents": json.loads((d / "agents").read_text())}}))
'''


def pane(tab, pane_id, cwd):
    return {"tab_id": tab, "pane_id": pane_id, "cwd": cwd}


# tab -> why it must be kept, or None when it is stale
PANES = [
    pane("t1", "p1", WT + "/fold-rest-22"),        # stale: worker gone, its worktree cwd
    pane("t2", "p2", WT + "/live-work-30"),        # a live worker
    pane("t3", "p3", CHECKOUT),                    # the lead, even with no agent listed
    pane("t4", "p4", "/w/other/.claude/worktrees/x-5"),  # another checkout's worker tab
    pane("t5", "p5", "/w/plugins-2/.claude/worktrees/y-6"),  # a sibling checkout sharing the prefix
    pane("t6", "p6", WT + "/split-31"),            # two panes, one still running an agent
    pane("t6", "p7", WT + "/split-31"),
    pane("t7", "p8", WT + "/deep-32/sub/dir"),     # stale, cwd below a worktree
]
AGENTS = [
    {"name": "live-work-30", "pane_id": "p2", "tab_id": "t2", "agent_status": "working"},
    {"name": "split-31", "pane_id": "p7", "tab_id": "t6", "agent_status": "idle"},
]


class TabSweep(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "herdr").write_text(FAKE)
        (self.tmp / "herdr").chmod(0o755)
        (self.tmp / "panes").write_text(json.dumps(PANES))
        (self.tmp / "agents").write_text(json.dumps(AGENTS))

    def sweep(self, *argv):
        env = dict(os.environ, FAKE=str(self.tmp), PATH=f"{self.tmp}:{os.environ['PATH']}")
        done = subprocess.run([sys.executable, str(BIN / "tab-sweep.py"), *argv],
                              env=env, capture_output=True, text=True, timeout=30)
        calls = [json.loads(l) for l in (self.tmp / "calls").read_text().splitlines()] if (self.tmp / "calls").exists() else []
        return done, calls

    def test_closes_only_agentless_tabs_under_this_checkouts_worktrees(self):
        done, calls = self.sweep(CHECKOUT)
        self.assertEqual(done.returncode, 0, done.stderr)
        closed = sorted(c[2] for c in calls if c[:2] == ["tab", "close"])
        self.assertEqual(closed, ["t1", "t7"])
        self.assertEqual(done.stdout.split(), ["t1", "t7"])

    def test_trailing_slash_checkout_is_the_same_checkout(self):
        done, calls = self.sweep(CHECKOUT + "/")
        self.assertEqual(sorted(c[2] for c in calls if c[:2] == ["tab", "close"]), ["t1", "t7"])

    def test_nothing_stale_closes_nothing(self):
        (self.tmp / "panes").write_text(json.dumps(PANES[1:7]))
        done, calls = self.sweep(CHECKOUT)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertFalse([c for c in calls if c[:2] == ["tab", "close"]])
        self.assertEqual(done.stdout, "")

    def test_usage(self):
        done, _ = self.sweep()
        self.assertEqual(done.returncode, 2)


if __name__ == "__main__":
    unittest.main()

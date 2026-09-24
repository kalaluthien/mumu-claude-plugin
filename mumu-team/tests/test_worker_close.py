"""`worker-close.py` run against a fake herdr that logs every call and plays a Claude session, with or without background work.

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
ISSUE = "https://github.com/o/r/issues/7"
OTHER = "SUBSCRIBE: other-8 https://github.com/o/r/issues/8\n"
LEAD = "GOAL: g\nMISSION: leader of https://github.com/o/r/issues/1\n"

# State lives in files under $FAKE: `alive` while the session runs, `background` when /exit meets the dialog, `dialog` while it shows,
# and `exiting` counts the polls a plain /exit takes to leave herdr's list.
FAKE = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
d, a = pathlib.Path(os.environ["FAKE"]), sys.argv[1:]
with open(d / "calls", "a") as f:
    f.write(json.dumps(a) + "\n")
alive, dialog, exiting = d / "alive", d / "dialog", d / "exiting"
if a[:2] == ["agent", "list"]:
    if exiting.exists():
        left = int(exiting.read_text()) - 1
        exiting.write_text(str(left))
        if not left:
            exiting.unlink()
            alive.unlink()
    agent = {"name": "close-7", "pane_id": "w1:p7", "tab_id": "w1:t7", "agent_status": "idle"}
    if (d / "session").exists():
        agent["agent_session"] = {"agent": "claude", "kind": "id", "value": (d / "session").read_text()}
    agents = [agent] if alive.exists() else []
    print(json.dumps({"result": {"agents": agents}}))
elif a[:2] == ["agent", "prompt"] and a[3] == "/exit" and not (d / "stuck").exists():
    if (d / "background").exists():
        dialog.touch()
    else:
        exiting.write_text("3")
elif a[:2] == ["agent", "read"]:
    print(" Background work is running\n ❯ 1. Exit\n   2. Keep running" if dialog.exists() else "❯")
elif a[:2] == ["agent", "send-keys"] and a[3:] == ["enter"] and dialog.exists():
    dialog.unlink()
    alive.unlink()
elif a[:2] == ["tab", "list"]:
    print(json.dumps({"result": {"tabs": [{"label": "close-7", "tab_id": "w1:t7"}, {"label": "other-8", "tab_id": "w1:t8"}]}}))
'''


class WorkerClose(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "herdr").write_text(FAKE)
        (self.tmp / "herdr").chmod(0o755)
        (self.tmp / "alive").touch()
        self.mission = self.tmp / "config" / "plugins" / "data" / "mumu-team-x" / "mission" / "s1.md"
        self.mission.parent.mkdir(parents=True)
        self.mission.write_text(LEAD + f"SUBSCRIBE: close-7 {ISSUE}\n" + OTHER)
        self.worker = self.mission.with_name("w7.md")
        self.worker.write_text(f"GOAL: g\nMISSION: worker on {ISSUE}\n")
        (self.tmp / "session").write_text("w7")

    def close(self):
        env = dict(os.environ, FAKE=str(self.tmp), PATH=f"{self.tmp}:{os.environ['PATH']}",
                   WORKER_CLOSE_TIMEOUT="1", WORKER_CLOSE_POLL="0.01",
                   CLAUDE_CONFIG_DIR=str(self.tmp / "config"), CLAUDE_CODE_SESSION_ID="s1")
        done = subprocess.run([sys.executable, str(BIN / "worker-close.py"), "close-7"],
                              env=env, capture_output=True, text=True, timeout=30)
        calls = [json.loads(l) for l in (self.tmp / "calls").read_text().splitlines()]
        return done, calls

    def assertClosed(self, done, calls):
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, "closed close-7\n")
        self.assertFalse((self.tmp / "alive").exists(), "session left running")
        self.assertEqual([c for c in calls if c[:2] == ["tab", "close"]], [["tab", "close", "w1:t7"]])
        self.assertEqual(self.mission.read_text(), LEAD + OTHER)
        self.assertFalse(self.worker.exists(), "worker mission left")

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

    def test_missing_worker_mission_is_no_error(self):
        self.worker.unlink()
        self.assertClosed(*self.close())

    def test_unknown_session_id_is_no_error_and_deletes_nothing(self):
        (self.tmp / "session").unlink()
        done, calls = self.close()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(self.worker.exists())
        self.assertEqual(self.mission.read_text(), LEAD + OTHER)

    def test_session_already_gone_still_closes_tab_and_line(self):
        (self.tmp / "alive").unlink()
        self.worker.unlink()
        done, calls = self.close()
        self.assertClosed(done, calls)
        self.assertFalse([c for c in calls if c[:2] == ["agent", "prompt"]])

    def test_session_that_never_exits_keeps_tab_and_line(self):
        (self.tmp / "stuck").touch()
        done, calls = self.close()
        self.assertEqual(done.returncode, 1)
        self.assertIn("herdr agent read w1:p7", done.stderr)
        self.assertFalse([c for c in calls if c[:2] == ["tab", "close"]])
        self.assertIn(f"SUBSCRIBE: close-7 {ISSUE}", self.mission.read_text())
        self.assertTrue(self.worker.exists(), "mission deleted while its session runs")


if __name__ == "__main__":
    unittest.main()

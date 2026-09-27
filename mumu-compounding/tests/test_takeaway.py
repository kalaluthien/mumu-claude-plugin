"""The harvest Stop hook `scripts/takeaway.py`, run on a fake transcript in an armed repository.

Run: python3 -m unittest discover mumu-compounding/tests
"""
import json
import os
import pathlib
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

HOOK = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "takeaway.py"
PROMPT = "Before you stop, harvest this session's work with the retro skill."
DREAM_PROMPT = "Memory files changed since the last dream: run the dream skill before you stop."


def calls(n):
    return [{"type": "assistant", "message": {"content": [{"type": "tool_use"}]}} for _ in range(n)]


def summary(minutes_ago, blocked):
    at = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return {"type": "system", "subtype": "stop_hook_summary",
            "timestamp": at.isoformat().replace("+00:00", "Z"),
            "hookErrors": [PROMPT] if blocked else []}


class Hook(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = pathlib.Path(tmp.name)
        self.repo = self.dir / "repo"
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.data = self.dir / "data"
        subprocess.run(["python3", str(HOOK), "arm", str(self.data)], cwd=self.repo, check=True,
                       capture_output=True)

    def reason(self, entries):
        transcript = self.dir / "projects" / "-repo" / "t.jsonl"
        transcript.parent.mkdir(parents=True, exist_ok=True)
        transcript.write_text("".join(json.dumps(e) + "\n" for e in entries))
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(self.data))
        for name in ("WORK_THRESHOLD", "HARVEST_INTERVAL", "DREAM_THRESHOLD"):
            env.pop(name, None)
        out = subprocess.run(["python3", str(HOOK)], env=env, capture_output=True, text=True, check=True,
                             input=json.dumps({"cwd": str(self.repo), "transcript_path": str(transcript)})).stdout
        return json.loads(out)["reason"] if out else None

    def blocks(self, entries):
        return self.reason(entries) == PROMPT


class Debounce(Hook):
    def after_block(self, minutes_ago, n):
        # the block, the harvest's own stop, then n calls
        return [summary(minutes_ago + 1, True)] + calls(3) + [summary(minutes_ago, False)] + calls(n)

    def test_enough_calls_within_the_interval_do_not_block(self):
        self.assertFalse(self.blocks(self.after_block(100, 40)))

    def test_enough_calls_after_the_interval_block(self):
        self.assertTrue(self.blocks(self.after_block(130, 40)))

    def test_few_calls_after_the_interval_do_not_block(self):
        self.assertFalse(self.blocks(self.after_block(130, 39)))

    def test_first_stop_with_enough_calls_blocks(self):
        self.assertTrue(self.blocks(calls(40)))

    def test_first_stop_with_few_calls_does_not_block(self):
        self.assertFalse(self.blocks(calls(39)))


def dream_typed(minutes_ago):
    at = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return {"type": "user", "timestamp": at.isoformat().replace("+00:00", "Z"),
            "message": {"content": "<command-name>/mumu-compounding:dream</command-name>"}}


class Dream(Hook):
    """Memory files changed since <data>/dreamed ask for a dream, once per build-up."""

    def setUp(self):
        super().setUp()
        self.stamp = self.data / "dreamed"
        self.stamp.touch()
        hour_ago = (datetime.now() - timedelta(hours=1)).timestamp()
        os.utime(self.stamp, (hour_ago, hour_ago))
        self.written = 0

    def write(self, n, minutes_ago=1):
        at = (datetime.now() - timedelta(minutes=minutes_ago)).timestamp()
        for _ in range(n):
            self.written += 1
            path = self.dir / "projects" / f"-pool{self.written % 2}" / "memory" / f"lesson-{self.written}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("a lesson\n")
            os.utime(path, (at, at))

    def test_changes_at_the_threshold_ask_for_a_dream(self):
        self.write(5)
        self.assertEqual(self.reason(calls(1)), DREAM_PROMPT)

    def test_changes_below_the_threshold_do_not(self):
        self.write(4)
        (self.dir / "projects" / "-pool0" / "memory" / "MEMORY.md").write_text("- index\n")
        self.assertIsNone(self.reason(calls(1)))

    def test_changes_before_the_last_dream_do_not(self):
        self.write(5, minutes_ago=120)
        self.assertIsNone(self.reason(calls(1)))

    def test_an_ask_resets_until_changes_build_up_anew(self):
        self.write(5)
        self.assertEqual(self.reason(calls(1)), DREAM_PROMPT)
        self.assertIsNone(self.reason(calls(2)))
        self.write(5, minutes_ago=-1)
        self.assertEqual(self.reason(calls(3)), DREAM_PROMPT)

    def test_a_dream_run_resets_and_its_own_edits_do_not_count(self):
        self.write(5)
        self.assertIsNone(self.reason([dream_typed(30)] + calls(1)))
        self.assertIsNone(self.reason(calls(2)))

    def test_a_stop_asking_a_harvest_does_not_ask_a_dream(self):
        self.write(5)
        self.assertEqual(self.reason(calls(40)), PROMPT)

    def test_sdk_sessions_are_not_asked(self):
        self.write(5)
        self.assertIsNone(self.reason([{"type": "user", "entrypoint": "sdk-cli"}] + calls(1)))

    def test_unarmed_repositories_are_not_asked(self):
        self.write(5)
        for path in (self.data / "armed").iterdir():
            path.unlink()
        self.assertIsNone(self.reason(calls(1)))

    def test_first_stop_starts_the_count(self):
        self.stamp.unlink()
        self.write(5)
        self.assertIsNone(self.reason(calls(1)))
        self.assertTrue(self.stamp.exists())


if __name__ == "__main__":
    unittest.main()

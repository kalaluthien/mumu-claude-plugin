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


def calls(n):
    return [{"type": "assistant", "message": {"content": [{"type": "tool_use"}]}} for _ in range(n)]


def summary(minutes_ago, blocked):
    at = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return {"type": "system", "subtype": "stop_hook_summary",
            "timestamp": at.isoformat().replace("+00:00", "Z"),
            "hookErrors": [PROMPT] if blocked else []}


class Debounce(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = pathlib.Path(tmp.name)
        self.repo = self.dir / "repo"
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.data = self.dir / "data"
        subprocess.run(["python3", str(HOOK), "arm", str(self.data)], cwd=self.repo, check=True,
                       capture_output=True)

    def blocks(self, entries):
        transcript = self.dir / "t.jsonl"
        transcript.write_text("".join(json.dumps(e) + "\n" for e in entries))
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(self.data))
        env.pop("WORK_THRESHOLD", None)
        env.pop("HARVEST_INTERVAL", None)
        out = subprocess.run(["python3", str(HOOK)], env=env, capture_output=True, text=True, check=True,
                             input=json.dumps({"cwd": str(self.repo), "transcript_path": str(transcript)})).stdout
        return bool(out) and json.loads(out)["decision"] == "block"

    def after_block(self, minutes_ago, n):
        # the block, the harvest's own stop, then n calls
        return [summary(minutes_ago + 1, True)] + calls(3) + [summary(minutes_ago, False)] + calls(n)

    def test_enough_calls_within_the_interval_do_not_block(self):
        self.assertFalse(self.blocks(self.after_block(10, 8)))

    def test_enough_calls_after_the_interval_block(self):
        self.assertTrue(self.blocks(self.after_block(40, 8)))

    def test_few_calls_after_the_interval_do_not_block(self):
        self.assertFalse(self.blocks(self.after_block(40, 7)))

    def test_first_stop_with_enough_calls_blocks(self):
        self.assertTrue(self.blocks(calls(8)))


if __name__ == "__main__":
    unittest.main()

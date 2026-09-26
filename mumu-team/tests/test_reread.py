"""The `UserPromptSubmit` hook of `hooks/hooks.json`, run as Claude Code runs it, on a copy of the plugin and a written transcript.

Run: python3 -m unittest discover mumu-team/tests
"""
import datetime
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
READ_AT = datetime.datetime(2026, 9, 26, 6, 0, tzinfo=datetime.timezone.utc)


class Reread(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.plugin = self.tmp / "mumu-team"
        shutil.copytree(ROOT / "bin", self.plugin / "bin")
        shutil.copytree(ROOT / "hooks", self.plugin / "hooks")
        self.refs = self.plugin / "skills" / "kickoff" / "references"
        self.refs.mkdir(parents=True)
        for name in ("work-task.md", "task.md", "routing.md"):
            (self.refs / name).write_text("rules\n")
            self.touch(name, changed=False)

    def touch(self, name, changed):
        """Set a file's mtime an hour before the reads, or an hour after."""
        at = (READ_AT + datetime.timedelta(hours=1 if changed else -1)).timestamp()
        os.utime(self.refs / name, (at, at))

    def prompt(self, *calls):
        """Run the hook on a transcript of `calls`, each a (tool, input) made at READ_AT; return the injected context."""
        transcript = self.tmp / "t.jsonl"
        lines = [{"type": "user", "timestamp": READ_AT.isoformat(), "message": {"role": "user", "content": "go"}}]
        lines += [{"type": "assistant", "timestamp": READ_AT.isoformat().replace("+00:00", "Z"),
                   "message": {"role": "assistant", "content": [{"type": "tool_use", "id": "t", "name": tool, "input": given}]}}
                  for tool, given in calls]
        transcript.write_text("".join(json.dumps(line) + "\n" for line in lines))
        payload = {"hook_event_name": "UserPromptSubmit", "session_id": "s", "transcript_path": str(transcript),
                   "cwd": str(self.tmp), "prompt": "see url"}
        commands = [h["command"] for entry in json.loads((self.plugin / "hooks" / "hooks.json").read_text())["hooks"]
                    .get("UserPromptSubmit", []) for h in entry["hooks"]]
        self.assertTrue(commands)
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(self.plugin))
        outs = [subprocess.run(c, shell=True, input=json.dumps(payload), env=env, capture_output=True, text=True, timeout=30)
                for c in commands]
        self.assertTrue(all(o.returncode == 0 for o in outs), outs)
        return "".join(json.loads(o.stdout)["hookSpecificOutput"]["additionalContext"] for o in outs if o.stdout.strip())

    def read(self, name):
        return "Read", {"file_path": str(self.refs / name)}

    def test_read_then_changed_names_that_file_once(self):
        self.touch("work-task.md", changed=True)
        context = self.prompt(self.read("work-task.md"))
        self.assertEqual(context.count(str(self.refs / "work-task.md")), 1, context)
        self.assertNotIn("routing.md", context)

    def test_read_by_bash_through_the_plugin_root_counts(self):
        self.touch("work-task.md", changed=True)
        command = f"cd {self.plugin}/skills/kickoff && cat references/work-task.md"
        self.assertIn("work-task.md", self.prompt(("Bash", {"command": command})))

    def test_read_and_unchanged_names_nothing(self):
        self.assertEqual(self.prompt(self.read("work-task.md"), self.read("routing.md")), "")

    def test_changed_but_never_read_names_nothing(self):
        self.touch("work-task.md", changed=True)
        self.touch("task.md", changed=True)
        self.assertEqual(self.prompt(self.read("routing.md")), "")
        self.assertEqual(self.prompt(), "")

    def test_a_name_inside_another_name_or_another_checkout_is_no_read(self):
        self.touch("task.md", changed=True)
        self.assertEqual(self.prompt(("Bash", {"command": f"cat {self.refs}/work-task.md"}),
                                     ("Bash", {"command": "cat /elsewhere/references/task.md"}),
                                     ("Read", {"file_path": "/elsewhere/references/task.md"})), "")

    def test_a_missing_transcript_names_nothing(self):
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(self.plugin))
        out = subprocess.run([str(self.plugin / "bin" / "reread.py")], input=json.dumps({"transcript_path": "/nope"}),
                             env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual((out.returncode, out.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()

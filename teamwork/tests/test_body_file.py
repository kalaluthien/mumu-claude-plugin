"""The kickoff Verbs rows that post a body pass it as a file, so text naming a raw merge posts past `bash-guard.py` (#294).

Run: uvx pytest teamwork/tests -q
"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOK = ROOT / "scripts" / "bash-guard.py"
SKILL = ROOT / "skills" / "kickoff" / "SKILL.md"
ROWS = {"comment": "gh issue comment", "file": "gh issue create", "pr": "gh pr create", "decide": "decision-post.py"}
FILLS = {"<url>": "https://github.com/o/r/issues/1", "<repo>": "o/r", "<title>": "Fix the thing", "<label>...": "effort:low",
         "<default>": "main", "<branch>": "b", "<pr>": "1", "[--criteria <file>] ": ""}
BODY = "## Goal\nNo `gh pr " + "merge 7` by hand.\n\n## Definition of done\nD1: a check -> passes\n"


def row(verb):
    line = next(l for l in SKILL.read_text().splitlines() if l.startswith(f"| `{verb}` |"))
    return [c for c in re.findall(r"`([^`]+)`", line) if c.startswith(ROWS[verb]) or " --body-file " in c]


def command(template, path):
    for key, value in FILLS.items():
        template = template.replace(key, value)
    if "<path>" in template:
        return template.replace("<path>", path)
    return f"{template} <<'EOF'\n{BODY}EOF"


class BodyFromFile(unittest.TestCase):
    def test_each_body_row_reads_a_file_not_a_heredoc(self):
        for verb in ROWS:
            with self.subTest(verb):
                commands = row(verb)
                self.assertTrue(commands)
                for c in commands:
                    self.assertIn("<path>", c)
                    self.assertNotIn("--body-file -", c)

    def test_each_row_command_with_a_body_naming_a_merge_passes_the_guard(self):
        for verb in ROWS:
            for template in row(verb):
                with self.subTest(verb=verb, template=template):
                    cwd = tempfile.mkdtemp()
                    (pathlib.Path(cwd) / "body.md").write_text(BODY)
                    payload = {"tool_input": {"command": command(template, "body.md")}, "cwd": cwd,
                               "agent_type": "teamwork:lead"}
                    result = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

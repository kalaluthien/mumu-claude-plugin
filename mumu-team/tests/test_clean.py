"""Each command of kickoff's `clean` verb, filled for a sample worker, matches a literal allow rule.

Run: uvx pytest mumu-team/tests -q
"""
import fnmatch
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "kickoff" / "SKILL.md"
NAME = "sample-topic-12-1"

# the allow rules of ~/.claude/settings.json as of kalaluthien/dotclaude#88
ALLOW = [
    "git worktree remove .claude/worktrees/*",
    "git worktree remove --force .claude/worktrees/*",
    "git worktree remove --force --force .claude/worktrees/*",
    "git branch -D *",
    "git push origin --delete *",
    "git pull --ff-only",
    "git pull --ff-only -q",
]
DENY = ["rm -rf .claude/worktrees/*..*"]
# read-only, or the hook removal this task leaves as it is
EXEMPT = ("git ls-remote ", "cmp -s", "rm <hooks>/pre-commit")


def clean_commands():
    """The backticked commands of the `clean` row, placeholders filled with NAME."""
    row = next(line for line in SKILL.read_text().splitlines() if line.startswith("| `clean` |"))
    spans = re.findall(r"`([^`]+)`", row.split("|")[2])
    return [re.sub(r"<(name|branch|worktree)>", NAME, s) for s in spans if re.match(r"(git|rm|cmp) ", s) and len(s.split()) > 2]


class Clean(unittest.TestCase):
    def test_row_names_commands(self):
        self.assertTrue(any(c.startswith("git worktree remove") for c in clean_commands()))

    def test_each_command_matches_an_allow_rule(self):
        for command in clean_commands():
            if command.startswith(EXEMPT):
                continue
            with self.subTest(command=command):
                self.assertNotRegex(command, r"[;&|$<>]|\bcd\b")
                self.assertFalse(any(fnmatch.fnmatchcase(command, p) for p in DENY))
                self.assertTrue(any(fnmatch.fnmatchcase(command, p) for p in ALLOW))


if __name__ == "__main__":
    unittest.main()

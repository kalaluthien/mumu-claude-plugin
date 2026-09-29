"""Each routine step the kickoff skill's Verbs and the judge write, placeholders filled, is one literal command an
owner allow rule matches, and `bash-guard.py` lets it through; a refused self-modifying edit reaches the owner as one
apply command (#281).

Run: uvx pytest mumu-teamwork/tests -q
"""
import fnmatch
import json
import pathlib
import re
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_clean import ALLOW  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "kickoff" / "SKILL.md"
JUDGE = ROOT / "agents" / "judge.md"
HOOK = ROOT / "scripts" / "bash-guard.py"
WORK = ROOT / "skills" / "kickoff" / "references" / "worker-playbook.md"
# rules already in the owner's ~/.claude/settings.json, fixed: the test adds no other
RULES = ALLOW + ["gh *", "worker-start.py *", "lead-start.py *", "session-close.py *", "pr-merge.py https://github.com/*"]
VERBS = ("start", "start-lead", "close", "merge")
PR = "https://github.com/kalaluthien/mumu-claude-plugin/pull/261"
VALUES = {
    "checkout": "/Users/me/workspace/plugins", "topic": "sample-topic", "model": "sonnet", "effort": "low",
    "task-url": "https://github.com/kalaluthien/mumu-claude-plugin/issues/12", "your address": "plugins-lead",
    "folder": "mumu-teamwork", "claude flags": "--model opus", "name": "sample-topic-12-1", "pr-url": PR,
    "url": "https://github.com/kalaluthien/mumu-claude-plugin/issues/12",
    "verdict lines": "APPROVED: 8bd0af5dbae98300d657961961b6954f760dd82c\nChecked the diff and each criterion.",
}
# no file, stdin, heredoc, pipe, `$(...)`, `;`, `&&`, loop, `git -C`, interpreter or path prefix
FORBIDDEN = re.compile(r"[;&|<>$`]|--body-file|\s-F\s|\bfor\b|\bgit -C\b|^(?:python\S*|bash|sh|zsh|uv|uvx|cd)\s|^\S*/")


def fill(command):
    """The command with each `<placeholder>` filled and each `[optional]` part kept."""
    return re.sub(r"<([^<>]+)>", lambda m: VALUES[m[1]], command.replace("[", "").replace("]", ""))


def verb_commands():
    """The first backticked command of each of `VERBS`' rows, filled."""
    found = {}
    for line in SKILL.read_text().splitlines():
        m = re.match(r"\| `([\w-]+)` \| `([^`]+)`", line)
        if m and m[1] in VERBS:
            found[m[1]] = fill(m[2])
    return found


def judge_commands():
    """Each `gh ... comment` command judge.md writes, filled."""
    return [fill(c) for c in re.findall(r"`(gh (?:pr|issue) comment [^`]+)`", JUDGE.read_text())]


def guard(command, agent=None):
    payload = {"tool_input": {"command": command}, "cwd": "."}
    if agent:
        payload["agent_type"] = agent
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload), capture_output=True, text=True)


class Literal(unittest.TestCase):
    def assert_literal(self, command, agent=None):
        self.assertNotRegex(command, FORBIDDEN)
        self.assertTrue(any(fnmatch.fnmatchcase(command, rule) for rule in RULES), command)
        result = guard(command, agent)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_each_verb_row_is_one_literal_command(self):
        commands = verb_commands()
        self.assertEqual(sorted(commands), sorted(VERBS))
        for verb, command in commands.items():
            with self.subTest(verb=verb, command=command):
                self.assert_literal(command)

    def test_the_judge_names_its_post_as_one_literal_command(self):
        commands = judge_commands()
        self.assertEqual(sorted(c.split()[1] for c in commands), ["issue", "pr"])
        for command in commands:
            with self.subTest(command=command):
                self.assertIn("\n", command)  # a verdict spans lines
                self.assert_literal(command, "mumu-teamwork:judge")

    def test_a_two_line_verdict_passes_the_guard_and_the_gh_rule(self):
        command = f"gh pr comment {PR} --body 'APPROVED: 8bd0af5dbae98300d657961961b6954f760dd82c\nChecked the diff at the head.'"
        self.assert_literal(command, "mumu-teamwork:judge")
        self.assertTrue(fnmatch.fnmatchcase(command, "gh *"))


class RefusedStep(unittest.TestCase):
    def rule(self):
        """`worker-playbook.md`'s bullet for a step auto mode refuses."""
        lines = [line for line in WORK.read_text().splitlines() if line.lstrip().startswith("- A step auto mode refuses")]
        self.assertEqual(len(lines), 1)
        return lines[0]

    def test_a_refused_self_modifying_edit_goes_to_the_owner_as_one_apply_command(self):
        rule = self.rule()
        self.assertIn("self-modifying edit, to a rules, guard or agent file", rule)
        self.assertIn("with the Write tool as a patch", rule)
        self.assertIn("exactly one owner command", rule)
        self.assertEqual(re.findall(r"`! [^`]+`", rule), ["`! git -C <worktree> apply <patch-path>`"])
        self.assertRegex(rule, r"then .*commit, push and finish to merge with no further owner turn\.$")


if __name__ == "__main__":
    unittest.main()

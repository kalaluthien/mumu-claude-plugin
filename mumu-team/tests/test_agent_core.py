"""Each role agent keeps its share of the default system prompt that `--agent` replaces.

Run: python3 -m unittest discover mumu-team/tests
"""
import pathlib
import re
import unittest

AGENTS = pathlib.Path(__file__).resolve().parent.parent / "agents"
MAX_WORDS = 250

# item of the default prompt -> a phrase its summary must hold
ITEMS = {
    "security": "Security:",
    "terminal markdown": "markdown in a terminal",
    "denied call": "denied tool call",
    "hooks": "Hook output is user feedback",
    "pasted content": "<pasted_content>",
    "dedicated tools": "dedicated file and search tools",
    "path:line": "`path:line`",
    "code style": "the code around it",
    "pronouns": "they/them",
    "confirm hard-to-reverse": "Confirm first any action that is hard to reverse",
    "publishing": "external service publishes it",
    "look before deleting": "before deleting or overwriting",
    "faithful reports": "Report faithfully",
    "bang command": "`! <command>`",
    "skills": "through Skill",
    "memory": "recalled memory",
    "context summarising": "summarized and continues",
    "act once informed": "With enough information, act",
}
ALL = set(ITEMS)
ROLES = {
    "lead": ALL,
    "worker": ALL - {"pasted content", "bang command"},
    "reviewer": {"security", "denied call", "dedicated tools", "path:line", "code style", "pronouns", "faithful reports", "act once informed"},
}


def core(role):
    """The body's `# Core` section, up to the next top-level heading."""
    text = (AGENTS / f"{role}.md").read_text()
    match = re.search(r"^# Core\n(.*?)(?=^# |\Z)", text, re.M | re.S)
    return match.group(1) if match else ""


class Core(unittest.TestCase):
    def test_each_role_holds_its_items(self):
        for role, items in ROLES.items():
            section = core(role)
            for item in sorted(items):
                with self.subTest(role=role, item=item):
                    self.assertIn(ITEMS[item], section)

    def test_each_summary_is_at_most_250_words(self):
        for role in ROLES:
            with self.subTest(role=role):
                words = len(core(role).split())
                self.assertTrue(0 < words <= MAX_WORDS, f"{role}: {words} words")


if __name__ == "__main__":
    unittest.main()

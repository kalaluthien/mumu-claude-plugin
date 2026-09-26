"""Each role agent keeps its share of the default system prompt that `--agent` replaces, and the one reviewer agent gets its model by the pull request's size.

Run: python3 -m unittest discover mumu-team/tests
"""
import importlib.machinery
import pathlib
import re
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
AGENTS = ROOT / "agents"
review = importlib.machinery.SourceFileLoader("review_model", str(ROOT / "bin" / "review-model.py")).load_module()
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


def git(repo, *args):
    subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True)


class ReviewModel(unittest.TestCase):
    def test_twenty_changed_lines_get_sonnet_and_twenty_one_get_opus(self):
        with tempfile.TemporaryDirectory() as repo:
            git(repo, "init", "-q", "-b", "main")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "base")
            git(repo, "checkout", "-q", "-b", "topic")
            path = pathlib.Path(repo, "f.txt")
            printed = []
            for n in (20, 21):
                path.write_text("".join(f"{i}\n" for i in range(n)))
                git(repo, "add", "f.txt")
                git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", str(n))
                out = subprocess.run([str(ROOT / "bin" / "review-model.py"), "main", "HEAD"], cwd=repo, capture_output=True, text=True, check=True)
                printed.append(out.stdout.strip())
                git(repo, "reset", "-q", "--hard", "main")
            self.assertEqual(printed, ["sonnet (20 changed lines)", "opus (21 changed lines)"])

    def test_insertions_and_deletions_both_count(self):
        self.assertEqual(review.changed(" 2 files changed, 10 insertions(+), 2 deletions(-)"), 12)
        self.assertEqual(review.changed(" 1 file changed, 1 deletion(-)"), 1)
        self.assertEqual(review.changed(""), 0)
        self.assertEqual(review.model_for(12), "sonnet")


class ReviewerAgent(unittest.TestCase):
    def test_one_reviewer_agent_defaults_to_opus(self):
        self.assertEqual(sorted(p.stem for p in AGENTS.glob("review*.md")), ["reviewer"])
        _, front, _ = (AGENTS / "reviewer.md").read_text().split("---\n", 2)
        self.assertIn("model: opus", front.splitlines())


if __name__ == "__main__":
    unittest.main()

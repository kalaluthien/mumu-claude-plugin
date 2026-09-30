"""What `skills/` holds: one skill, `contract`, whose tables route to playbooks that exist, and no path into it dangles.

Run: python3 -m unittest discover checkerwork/tests
"""
import pathlib
import re
import unittest

PLUGIN = pathlib.Path(__file__).resolve().parent.parent
SKILL = PLUGIN / "skills" / "contract"
TABLE_LINK = re.compile(r"^\|.*\]\(([^)#]+\.md)\)", re.M)
ROOT_PATH = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)")
JOINED = re.compile(r'"skills" / "([^"]+)"(?: / "([^"]+)")?(?: / "([^"]+)")?')


def routes(page):
    """The markdown files a page's table rows link to, resolved from the page's folder."""
    return [page.parent / m for m in TABLE_LINK.findall(page.read_text())]


class Skills(unittest.TestCase):
    def test_one_skill_named_contract(self):
        self.assertEqual(sorted(p.name for p in (PLUGIN / "skills").iterdir() if p.is_dir()), ["contract"])
        self.assertIn("name: contract\n", (SKILL / "SKILL.md").read_text())

    def test_skill_routes_to_each_playbook(self):
        got = routes(SKILL / "SKILL.md")
        self.assertEqual(sorted({p.name for p in got}), ["eval.md", "spec.md", "test.md"])
        for p in got:
            self.assertTrue(p.is_file(), p)

    def test_eval_routes_to_its_sub_playbooks(self):
        got = routes(SKILL / "references" / "eval.md")
        self.assertEqual(sorted({p.name for p in got}), ["eval-analysis.md", "eval-climb.md", "eval-graders.md", "eval-judge.md"])
        for p in got:
            self.assertTrue(p.is_file(), p)

    def test_rules_live_in_the_skill_body(self):
        self.assertEqual(list((PLUGIN / "lib").glob("*.md")), [])
        body = (SKILL / "SKILL.md").read_text()
        for heading in ("## Rules", "## Breaking a check", "| failure mode |"):
            self.assertIn(heading, body)

    def test_no_path_into_the_plugin_dangles(self):
        named = 0
        for f in PLUGIN.rglob("*"):
            if not f.is_file() or f.suffix not in (".md", ".py", ".json", ".sh") or "results" in f.parts or f.name == "test_skills.py":
                continue
            text = f.read_text(errors="replace")
            for rel in ROOT_PATH.findall(text):
                named += 1
                self.assertTrue((PLUGIN / rel.rstrip(".")).exists(), f"{f.relative_to(PLUGIN)} names {rel}")
            for parts in JOINED.findall(text):
                named += 1
                path = PLUGIN.joinpath("skills", *(p for p in parts if p))
                self.assertTrue(path.exists(), f"{f.relative_to(PLUGIN)} names {path.relative_to(PLUGIN)}")
        self.assertGreater(named, 5)


if __name__ == "__main__":
    unittest.main()

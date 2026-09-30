"""What `skills/` holds: one skill, `contract`, whose one table routes to each mode #368 decided, and no path into it dangles.

Run: python3 -m unittest discover checkerwork/tests
"""
import pathlib
import re
import unittest

PLUGIN = pathlib.Path(__file__).resolve().parent.parent
SKILL = PLUGIN / "skills" / "contract"
REFS = SKILL / "references"
MODES = ["eval-audit", "eval-calibrate", "eval-compare", "eval-optimize", "eval-triage", "eval-write", "spec-verify",
         "spec-write", "test-audit", "test-probe", "test-write"]
OLD = [a + "-" + b for a, b in (("eval", "setup"), ("test", "setup"), ("spec", "setup"), ("eval", "judge"), ("test", "add"),
                              ("test", "prune"), ("spec", "change"))]
TABLE_LINK = re.compile(r"^\|.*\]\(([^)#]+\.md)\)", re.M)
LINK = re.compile(r"\]\(([^)#]+\.md)\)")
TOPIC = re.compile(r"^(eval|test|spec)/[a-z-]+-playbook\.md$")
ROOT_PATH = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)")
JOINED = re.compile(r'"skills" / "([^"]+)"(?: / "([^"]+)")?(?: / "([^"]+)")?')


def links(page, pattern=LINK):
    """The markdown files a page links to, resolved from the page's folder."""
    return [(page.parent / m).resolve() for m in pattern.findall(page.read_text())]


class Skills(unittest.TestCase):
    def test_one_skill_named_contract(self):
        self.assertEqual(sorted(p.name for p in (PLUGIN / "skills").iterdir() if p.is_dir()), ["contract"])
        self.assertIn("name: contract\n", (SKILL / "SKILL.md").read_text())

    def test_skill_routes_by_one_table_to_each_mode(self):
        got = links(SKILL / "SKILL.md", TABLE_LINK)
        self.assertEqual(sorted(p.relative_to(REFS.resolve()).as_posix() for p in got), [f"{m}.md" for m in MODES])
        for p in got:
            self.assertTrue(p.is_file(), p)

    def test_setup_is_the_first_step_of_a_change_mode(self):
        self.assertEqual(len(MODES), 11)
        for mode, layout in (("test-write", "test layout"), ("spec-write", "model")):
            first = (REFS / f"{mode}.md").read_text().split("\n1. ", 1)[1].split("\n", 1)[0]
            self.assertTrue(first.startswith(f"A repo with no {layout}, only then:"), mode)
        for f in PLUGIN.rglob("*"):
            if f.is_file() and f.suffix in (".md", ".py", ".json", ".sh") and f.name != "test_skills.py":
                self.assertIsNone(re.search("|".join(OLD), f.read_text(errors="replace")), f.name)

    def test_eval_compare_reads_only_shared_playbooks(self):
        got = links(REFS / "eval-compare.md")
        self.assertTrue(got)
        for p in got:
            self.assertRegex(p.relative_to(REFS.resolve()).as_posix(), TOPIC)

    def test_no_mode_routes_to_another_mode(self):
        modes = {(REFS / f"{m}.md").resolve() for m in MODES}
        for m in modes:
            self.assertEqual([p for p in links(m) if p in modes], [], m.name)

    def test_every_other_file_is_a_topic_a_mode_links(self):
        linked = {p for m in MODES for p in links(REFS / f"{m}.md")}
        for f in REFS.rglob("*"):
            rel = f.relative_to(REFS).as_posix()
            if f.is_dir() or rel in {f"{m}.md" for m in MODES}:
                continue
            self.assertRegex(rel, TOPIC)
            self.assertIn(f.resolve(), linked, rel)
        for p in {p for m in MODES for p in links(REFS / f"{m}.md")} | {p for f in REFS.rglob("*.md") for p in links(f)}:
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

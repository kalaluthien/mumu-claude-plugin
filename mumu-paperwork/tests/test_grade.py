"""grade.py's calculations: parsing a reply, settling three graders, agreement and kappa, dropping a judge step.

Run: uvx --with playwright pytest mumu-paperwork/tests -q
"""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("grade", ROOT / "skills" / "typesetting" / "scripts" / "grade.py")
grade = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(grade)


class Grade(unittest.TestCase):
    def test_scores_read_the_last_json_block(self):
        reply = 'Focus: fine.\n```json\n{"Focus": 1}\n```\nOn reflection:\n```json\n{"Focus": 3, "Controls": "N/A"}\n```'
        self.assertEqual(grade.scores(reply, ["Focus", "Controls", "Feedback"]),
                         {"Focus": 3, "Controls": "n/a", "Feedback": None})

    def test_settle(self):
        self.assertEqual(grade.settle([1, 3, 2]), 2)
        self.assertEqual(grade.settle([1, "n/a", 3]), 1)
        self.assertEqual(grade.settle(["n/a", 2, "n/a"]), "n/a")

    def test_agreement_counts_na_against_a_number_as_a_miss(self):
        self.assertEqual(grade.agreement([(3, 3), (2, 3), (0, 2), ("n/a", "n/a"), ("n/a", 1)]), (0.25, 0.5, 4))

    def test_kappa(self):
        self.assertEqual(grade.kappa([(1, 1), (2, 2), (3, 3)]), 1)
        self.assertEqual(grade.kappa([(3, 3), (3, 3)]), None)
        self.assertAlmostEqual(grade.kappa([(1, 1), (1, 2), (2, 2), (2, 1)]), 0)

    def test_without_drops_only_that_step(self):
        rubric = "## Judge procedure\n\n1. **A.** one\n   Shown: x\n2. **B.** two\n3. **C.** three\n"
        self.assertEqual(grade.without(rubric, {2}), "## Judge procedure\n\n1. **A.** one\n   Shown: x\n3. **C.** three\n")

    def test_blind_strips_the_provenance_line_and_names_neutrally(self):
        path = ROOT / "tests" / "rubric" / "technical-weak-readme.md"
        text, name = grade.blind(path)
        self.assertFalse(text.startswith("<!--"))
        self.assertRegex(name, r"^doc-\d{3}\.md$")
        self.assertNotIn("weak", name)


if __name__ == "__main__":
    unittest.main()

"""The rubric's shape: each criterion has a definition, levels 3 to 0, its kinds and two or more sources, under a dimension.

Run: uvx --with playwright pytest mumu-document/tests -q
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUBRIC = ROOT / "skills" / "writing-documents" / "references" / "rubric.md"
SKILL = ROOT / "skills" / "writing-documents" / "SKILL.md"
DIMENSIONS = ["Content", "Structure", "Language", "Visual", "Interaction"]


def criteria(text):
    """{(dimension, criterion): body} for each h3 under an h2."""
    out, dimension = {}, None
    for block in re.split(r"(?m)^(?=#{2,3} )", text):
        head, _, body = block.partition("\n")
        if head.startswith("## "):
            dimension = head[3:].strip()
        elif head.startswith("### "):
            out[(dimension, head[4:].strip())] = body
    return out


def failures(text):
    out, found = [], criteria(text)
    dimensions = list(dict.fromkeys(d for d, _ in found))
    if dimensions != DIMENSIONS:
        out.append(f"dimensions {dimensions} != {DIMENSIONS}")
    for (dimension, name), body in found.items():
        where = f"{dimension} / {name}"
        if not re.match(r"\s*\S", body.split("\n- ")[0]):
            out.append(f"{where}: no definition")
        kinds = re.search(r"Kinds:\s+(static|interactive|both)\.", body)
        if not kinds:
            out.append(f"{where}: no Kinds: static, interactive or both")
        elif dimension == "Interaction" and kinds.group(1) != "interactive":
            out.append(f"{where}: an interaction criterion applies to {kinds.group(1)}")
        levels = re.findall(r"(?m)^- (\d):", body)
        if levels not in (["3", "2", "1", "0"], ["3", "2", "1"]):
            out.append(f"{where}: levels {levels}, not 3 to 0")
        sources = re.search(r"Sources: (.*?)(?:\n\n|\Z)", body, re.S)
        if not sources or len(sources.group(1).split(";")) < 2:
            out.append(f"{where}: fewer than 2 sources")
    return out


class Rubric(unittest.TestCase):
    def test_rubric_passes(self):
        self.assertEqual(failures(RUBRIC.read_text()), [])

    def test_judge_procedure(self):
        procedure = RUBRIC.read_text().split("## Judge procedure", 1)[1]
        steps = re.findall(r"(?m)^\d\. \*\*([^*]+)\*\*", procedure)
        self.assertEqual(steps, ["Blind.", "One at a time.", "Evidence first.", "Length earns nothing.",
                                 "Two graders.", "Anchor set."])

    def test_skill_reread_grades_against_rubric(self):
        done = SKILL.read_text().split("## Done when", 1)[1]
        self.assertRegex(done, r"Reread[^\n]*\n[^\n]*\[rubric\.md\]\(references/rubric\.md\)")

    def test_each_check_fails_its_break(self):
        good = RUBRIC.read_text()
        breaks = {
            "one source": re.sub(r"Sources: Nielsen 1994 \(visibility[^\n]*\n[^\n]*\n[^\n]*\n",
                                 "Sources: Nielsen 1994.\n", good, count=1),
            "no kinds": good.replace("Kinds: both.", "", 1),
            "five levels": good.replace("- 3: all five hold.", "- 4: more.\n- 3: all five hold.", 1),
            "a dimension renamed": good.replace("## Visual", "## Look", 1),
            "interaction on static": re.sub(r"Kinds:(\s+)interactive\.", r"Kinds:\1both.", good, count=1),
        }
        for name, text in breaks.items():
            with self.subTest(name):
                self.assertNotEqual(text, good)
                self.assertTrue(failures(text), name)


if __name__ == "__main__":
    unittest.main()

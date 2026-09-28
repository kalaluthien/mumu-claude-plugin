"""The rubric's shape: each criterion has a definition, levels 3 to 0 each with an example, its kinds and two or more
sources, under a dimension; the judge steps each say whether their effect was shown; the answer key scores every
criterion on every anchor.

Run: uvx --with playwright pytest mumu-paperwork/tests -q
"""
import json
import pathlib
import re
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUBRIC = ROOT / "skills" / "typesetting" / "references" / "rubric.md"
SKILL = ROOT / "skills" / "typesetting" / "SKILL.md"
ANCHORS = ROOT / "tests" / "rubric"
KEY = ANCHORS / "answer-key.json"
DIMENSIONS = ["Content", "Structure", "Language", "Visual", "Interaction"]
DISCOURSE = {("Structure", "Narrative"), ("Structure", "Pyramid and MECE"), ("Structure", "Emphasis"),
             ("Language", "Coherence")}
STEPS = ["Blind.", "One at a time.", "Evidence first.", "Length earns nothing.", "Two graders.", "Anchor set."]


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
    out, found = [], criteria(text.split("## Judge procedure", 1)[0])
    for missing in sorted(DISCOURSE - found.keys()):
        out.append(f"no discourse criterion {' / '.join(missing)}")
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
        for level, item in re.findall(r"(?ms)^- (\d):(.*?)(?=^- \d:|^Sources:|\Z)", body):
            if not re.search(r"(?m)^  Example: \S", item):
                out.append(f"{where}: level {level} has no example")
        sources = re.search(r"Sources: (.*?)(?:\n\n|\Z)", body, re.S)
        if not sources or len(sources.group(1).split(";")) < 2:
            out.append(f"{where}: fewer than 2 sources")
    return out


def step_failures(text):
    """Each judge step in order, with a body and a line saying `Shown:` or `Unproven:`."""
    procedure = text.split("## Judge procedure", 1)[1]
    blocks = re.findall(r"(?ms)^\d\. \*\*([^*]+)\*\*(.*?)(?=^\d\. \*\*|\Z)", procedure)
    out = [] if [s for s, _ in blocks] == STEPS else [f"steps {[s for s, _ in blocks]} != {STEPS}"]
    for step, body in blocks:
        said = re.split(r"(?m)^\s*(?:Shown|Unproven):", body)[0]
        if len(said.split()) < 8:
            out.append(f"{step} has no body")
        if not re.search(r"(?m)^   (Shown|Unproven): \S", body):
            out.append(f"{step} says neither Shown: nor Unproven:")
    return out


def key_failures(text, key_path):
    """Every anchor has a score for every criterion: 0 to 3, or n/a."""
    names = [c for _, c in criteria(text.split("## Judge procedure", 1)[0])]
    anchors = sorted(p.name for p in ANCHORS.iterdir() if p.suffix in (".md", ".html"))
    if not key_path.exists():
        return [f"no answer key {key_path.name}"]
    key, out = json.loads(key_path.read_text()), []
    for anchor in anchors:
        for name in names:
            score = key.get(anchor, {}).get(name)
            if score not in (0, 1, 2, 3, "n/a"):
                out.append(f"{anchor} / {name}: {score!r}, not 0 to 3 or n/a")
    out += [f"{extra}: not an anchor" for extra in sorted(set(key) - set(anchors))]
    return out


class Rubric(unittest.TestCase):
    def test_rubric_passes(self):
        self.assertEqual(failures(RUBRIC.read_text()), [])

    def test_judge_procedure(self):
        self.assertEqual(step_failures(RUBRIC.read_text()), [])

    def test_answer_key(self):
        self.assertEqual(key_failures(RUBRIC.read_text(), KEY), [])

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
            "a level with no example": re.sub(r"\n  Example: [^\n]*(\n    [^\n]*)*", "", good, count=1),
            "no emphasis": good.replace("### Emphasis", "### Stress", 1),
        }
        for name, text in breaks.items():
            with self.subTest(name):
                self.assertNotEqual(text, good)
                self.assertTrue(failures(text), name)
        emptied = re.sub(r"(?m)^(3\. \*\*Evidence first\.\*\*).*\n(?:   .*\n)*", r"\1\n", good)
        with self.subTest("a judge step emptied"):
            self.assertNotEqual(emptied, good)
            self.assertTrue(step_failures(emptied))
        key = json.loads(KEY.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            for name, broken in {"an anchor with no entry": {k: v for k, v in list(key.items())[1:]},
                                 "a criterion with no entry": {k: {c: s for c, s in v.items() if c != "Emphasis"}
                                                               for k, v in key.items()},
                                 "a score out of range": {k: {**v, "Focus": 4} for k, v in key.items()}}.items():
                path = pathlib.Path(tmp) / "key.json"
                path.write_text(json.dumps(broken))
                with self.subTest(name):
                    self.assertTrue(key_failures(good, path))


if __name__ == "__main__":
    unittest.main()

"""`skill-check.py` on the real skill and on broken copies: each check can fail.

Run: uvx --with playwright pytest mumu-document/tests -q
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECK = ROOT / "skills" / "writing-documents" / "scripts" / "skill-check.py"
SKILL = ROOT / "skills" / "writing-documents"
W, SKIN = "references/artifact/widgets/", "references/artifact/shared/skin.css"
# (file, [(old, new), ...], a regex the output must match; None when the copy must pass)
CASES = [
    ("SKILL.md", [("| `chart` `bar` |", "| `sankey` |")], r"unknown widget `sankey`"),
    ("SKILL.md", [("| change over time", "| a trend in a list | `chart` `line` | a list |\n| change over time")], None),
    ("SKILL.md", [("`chart` `bar`", "`chart` `bubble`")], r"`bubble` is not in chart\.html's spec"),
    ("SKILL.md", [("`chart` `bar`", "`chart`")], r"names `chart` but none of its kinds"),
    (W + "chart.html", [("fill: var(--text); }", "fill: #000; }")], r"chart\.html"),
    (W + "diagram.html", [("--diagram-indent: var(--sp-4)", "--diagram-indent: 8px")], r"diagram\.html:\d+: literal size: 8px"),
    (W + "diagram.html", [('<path class="lifeline"', '<path style="transition: stroke .3s" class="lifeline"')], r"literal size: \.3s"),
    (W + "diagram.html", [('width="520"', 'width="524"')], None),
    (W + "diagram.html", [("--diagram-indent: var(--sp-4)", "--diagram-indent: var(--sp-9)")], r"token --sp-9 is not in skin\.css"),
    (W + "diagram.html", [("--diagram-indent: var(--sp-4)", "--diagram-indent: var(--p-white)")], r"reads primitive --p-white"),
    (W + "diagram.html", [("--diagram-indent: var(--sp-4);", "--diagram-indent: var(--sp-4); --diagram-x: var(--sp-1);")], None),
    ("references/artifact/shared/swipe.html", [("flex: 0 0 85%;", "flex: 0 0 20rem;")], r"literal size: 20rem"),
    (SKIN, [("light-dark(#d55e00,", "light-dark(#f5c9a8,")], r"--kind-2 on --fill light"),
    (SKIN, [("--p-grey-500: #757575", "--p-grey-500: #c0c0c0")], r"--muted on --bg light"),
    (SKIN, [("#8a8a8a", "#3a3d42")], r"--border on --fill dark"),
    (SKIN, [("#057dbc", "#7fc4ea")], r"--link on --bg light"),
    (SKIN, [("  --accent:", "  --link:")], r"no role --accent"),
    # sky blue and lavender stay apart to a normal eye and pass 3:1 on black, but merge for a deuteranope
    (SKIN, [("light-dark(#cc79a7, #cc79a7)", "light-dark(#cc79a7, #a9a0e8)")],
     r"(?s)^(?!.*normal).*--kind-1 and --kind-4 dark deuteranopia ΔE \d+\.\d < 10"),
]


def run(skill):
    r = subprocess.run([sys.executable, str(CHECK), str(skill)], capture_output=True, text=True)
    return r.returncode, r.stdout


class SkillCheck(unittest.TestCase):
    def test_real_skill_passes(self):
        self.assertEqual(run(SKILL), (0, "pass\n"))

    def test_each_broken_copy(self):
        for name, edits, want in CASES:
            with self.subTest(f"{name}: {edits[0][1][:40]}"), tempfile.TemporaryDirectory() as d:
                skill = pathlib.Path(d) / "skill"
                shutil.copytree(SKILL, skill)
                text = (skill / name).read_text()
                for old, new in edits:
                    self.assertIn(old, text)
                    text = text.replace(old, new, 1)
                (skill / name).write_text(text)
                code, out = run(skill)
                if want is None:
                    self.assertEqual((code, out), (0, "pass\n"))
                else:
                    self.assertEqual(code, 1, out)
                    self.assertRegex(out, want)


if __name__ == "__main__":
    unittest.main()

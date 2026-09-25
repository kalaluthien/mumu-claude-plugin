"""`skill-check.py` on the real skill and on broken copies: each check can fail.

Run: for d in mumu-document/scripts/*/; do python3 -m unittest discover -s "$d"; done
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHECK = ROOT / "scripts" / "skill" / "skill-check.py"
SKILL = ROOT / "skills" / "writing-documents"
W, SKIN = "references/artifact/widgets/", "references/artifact/shared/skin.css"
# (file, [(old, new), ...], a regex the output must match; None when the copy must pass)
CASES = [
    ("SKILL.md", [("| `table` |", "| `sankey` |")], r"unknown widget `sankey`"),
    ("SKILL.md", [("| rows sharing columns", "| a timeline | `table` | a list |\n| rows sharing columns")], None),
    ("SKILL.md", [("`chart` `scatter`", "`chart` `bubble`")], r"`bubble` is not in chart\.html's spec"),
    ("SKILL.md", [("`chart` `scatter`", "`chart`")], r"names `chart` but none of its kinds"),
    (W + "table.html", [("var(--fill)", "#fff")], r"table\.html"),
    (W + "table.html", [("--table-pad: var(--sp-2) var(--sp-3)", "--table-pad: 8px var(--sp-3)")], r"table\.html:\d+: literal size: 8px"),
    (W + "diagram.html", [('<path class="lifeline"', '<path style="transition: stroke .3s" class="lifeline"')], r"literal size: \.3s"),
    (W + "diagram.html", [('width="520"', 'width="524"')], None),
    (W + "table.html", [("var(--sp-2)", "var(--sp-9)")], r"token --sp-9 is not in skin\.css"),
    (W + "table.html", [("--table-hover: var(--bg)", "--table-hover: var(--p-white)")], r"reads primitive --p-white"),
    (W + "table.html", [("--table-hover: var(--bg);", "--table-hover: var(--bg); --table-x: var(--sp-1);")], None),
    (W + "diagram.html", [("  keyboard:", "  keys:")], r"diagram\.html: spec has no `keyboard:`"),
    (W + "diagram.html", [("disabled: none, played", "none, played")], r"diagram\.html: states name no `disabled`"),
    ("references/artifact/shared/swipe.html", [("flex: 0 0 85%;", "flex: 0 0 20rem;")], r"literal size: 20rem"),
    (SKIN, [("--motion: 200ms", "--motion: 400ms")], r"--motion is 400ms, not at most 200ms"),
    (SKIN, [("light-dark(#d55e00,", "light-dark(#f5c9a8,")], r"--kind-2 on --fill light"),
    (SKIN, [("--radius-s: 0;", "--corner: 0;")], r"no --radius-\* token"),
    (SKIN, [("--p-grey-500: #757575", "--p-grey-500: #c0c0c0")], r"--muted on --bg light"),
    (SKIN, [("#8a8a8a", "#3a3d42")], r"--border on --fill dark"),
    (SKIN, [("#057dbc", "#7fc4ea")], r"--link on --bg light"),
    (SKIN, [("  --accent:", "  --link:")], r"no role --accent"),
    # sky blue and lavender stay apart to a normal eye and pass 3:1 on black, but merge for a deuteranope
    (SKIN, [("light-dark(#cc79a7, #cc79a7)", "light-dark(#cc79a7, #a9a0e8)")],
     r"(?s)^(?!.*normal).*--kind-1 and --kind-4 dark deuteranopia ΔE \d+\.\d < 10"),
    (SKIN, [("--seq-2: light-dark(#9dc6e8", "--seq-2: light-dark(#509dcf"), ("--seq-3: light-dark(#509dcf", "--seq-3: light-dark(#9dc6e8")],
     r"--seq-2 and --seq-3 light"),
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

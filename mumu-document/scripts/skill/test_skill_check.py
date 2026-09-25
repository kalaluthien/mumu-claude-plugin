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


def run(skill):
    r = subprocess.run([sys.executable, str(CHECK), str(skill)], capture_output=True, text=True)
    return r.returncode, r.stdout


class SkillCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp()) / "skill"
        shutil.copytree(SKILL, self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp.parent)

    def edit(self, name, old, new):
        f = self.tmp / name
        text = f.read_text()
        self.assertIn(old, text)
        f.write_text(text.replace(old, new, 1))

    def test_real_skill_passes(self):
        self.assertEqual(run(SKILL), (0, "pass\n"))

    def test_unknown_widget_fails(self):
        self.edit("SKILL.md", "| `table` |", "| `chart` |")
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("unknown widget `chart`", out)

    def test_added_row_with_its_widget_passes(self):
        self.edit("SKILL.md", "| rows sharing columns", "| a timeline | `table` | a list |\n| rows sharing columns")
        self.assertEqual(run(self.tmp), (0, "pass\n"))

    def test_literal_colour_in_widget_fails(self):
        self.edit("references/page/widgets/table.html", "var(--fill)", "#fff")
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("table.html", out)

    def test_literal_size_in_widget_fails(self):
        self.edit("references/page/widgets/table.html", "--table-pad: var(--sp-2) var(--sp-3)", "--table-pad: 8px var(--sp-3)")
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertRegex(out, r"table\.html:\d+: literal size: 8px")

    def test_literal_duration_in_style_attribute_fails(self):
        self.edit("references/page/widgets/use-case.html", '<path class="lifeline"', '<path style="transition: stroke .3s" class="lifeline"')
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("literal size: .3s", out)

    def test_svg_geometry_is_not_a_size(self):
        self.edit("references/page/widgets/use-case.html", 'width="520"', 'width="524"')
        self.assertEqual(run(self.tmp), (0, "pass\n"))

    def test_unknown_token_fails(self):
        self.edit("references/page/widgets/table.html", "var(--sp-2)", "var(--sp-9)")
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("token --sp-9 is not in skin.css", out)

    def test_slow_motion_fails(self):
        self.edit("references/page/skin.css", "--p-ms-200: 200ms", "--p-ms-200: 400ms")
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("--motion is 400ms, not at most 200ms", out)

    def test_primitive_in_widget_fails(self):
        self.edit("references/page/widgets/table.html", "--table-hover: var(--bg)", "--table-hover: var(--p-white)")
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("reads primitive --p-white", out)

    def test_widget_token_passes(self):
        self.edit("references/page/widgets/table.html", "--table-hover: var(--bg);", "--table-hover: var(--bg); --table-x: var(--sp-1);")
        self.assertEqual(run(self.tmp), (0, "pass\n"))

    def test_spec_field_missing_fails(self):
        self.edit("references/page/widgets/use-case.html", "  keyboard:", "  keys:")
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("use-case.html: spec has no `keyboard:`", out)

    def test_spec_state_missing_fails(self):
        self.edit("references/page/widgets/use-case.html", "disabled: none, played", "none, played")
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("use-case.html: states name no `disabled`", out)

    def test_literal_size_in_player_fails(self):
        self.edit("references/page/widgets/use-case.html", "min-width: 0;", "min-width: 8rem;")
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("literal size: 8rem", out)

    def test_low_palette_contrast_fails(self):
        self.edit("references/page/skin.css", "--p-cat-2: #0f7f74", "--p-cat-2: #9fd8d2")
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("--kind-2 on --fill light", out)

    def test_missing_token_kind_fails(self):
        self.edit("references/page/skin.css", "--radius-s: 4px;", "--corner: 4px;")
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("no --radius-* token", out)

    def test_low_text_contrast_fails(self):
        self.edit("references/page/skin.css", "--p-ink-600: #5b5f66", "--p-ink-600: #c0c0c0")
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("--muted on --bg light", out)

    def test_low_border_contrast_in_dark_fails(self):
        self.edit("references/page/skin.css", "--p-ink-500: #767a82", "--p-ink-500: #3a3d42")
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("--border on --fill dark", out)

    def test_missing_role_fails(self):
        self.edit("references/page/skin.css", "  --accent:", "  --link:")
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("no role --accent", out)


if __name__ == "__main__":
    unittest.main()

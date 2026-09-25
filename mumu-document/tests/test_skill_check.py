"""`skill-check.py` on the real skill and on broken copies: each check can fail.

Run: python3 -m unittest discover mumu-document/tests
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECK = ROOT / "bin" / "skill-check.py"
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
        self.edit("widgets/table.html", "var(--fill)", "#fff")
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("table.html", out)

    def test_low_text_contrast_fails(self):
        self.edit("skin.css", "--muted: light-dark(#5b5f66,", "--muted: light-dark(#c0c0c0,")
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("--muted on --bg light", out)

    def test_low_border_contrast_in_dark_fails(self):
        self.edit("skin.css", "#767a82)", "#3a3d42)")
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("--border on --fill dark", out)

    def test_missing_role_fails(self):
        self.edit("skin.css", "--accent:", "--link:")
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("no role --accent", out)


if __name__ == "__main__":
    unittest.main()

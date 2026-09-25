"""`page-check.sh` fails a figure whose labels collide or leave it (run as in test_skill_check)."""
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECK = ROOT / "bin" / "page-check.sh"
CHROME = pathlib.Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
PAGE = """<!doctype html><html lang="ko"><meta charset="utf-8"><title>그림</title>
<main><svg width="280" height="80" viewBox="0 0 280 80">
<text x="8" y="24" font-size="14">작업자</text>
<text x="160" y="24" font-size="14">저장소</text>
</svg></main></html>"""


def run(html):
    with tempfile.TemporaryDirectory() as d:
        page = pathlib.Path(d) / "page.html"
        page.write_text(html)
        r = subprocess.run(["sh", str(CHECK), str(page)], capture_output=True, text=True)
        return r.returncode, r.stdout


@unittest.skipUnless(CHROME.exists(), "no Chrome")
class LabelGeometry(unittest.TestCase):
    def test_apart_labels_pass(self):
        code, out = run(PAGE)
        self.assertEqual(code, 0, out)
        self.assertIn("labels 0", out)

    def test_overlapping_labels_fail(self):
        code, out = run(PAGE.replace('x="160"', 'x="24"'))
        self.assertEqual(code, 1)
        self.assertIn("labels 2 FAIL", out)

    def test_label_outside_its_figure_fails(self):
        code, out = run(PAGE.replace('x="160"', 'x="250"'))
        self.assertEqual(code, 1)
        self.assertIn("labels 1 FAIL", out)


if __name__ == "__main__":
    unittest.main()

"""`chart-check.py` passes the gallery's charts and fails a chart whose marks, text alternative or keyboard path are wrong."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHECK = ROOT / "scripts" / "chart" / "chart-check.py"
GALLERY = ROOT / "scripts" / "artifact" / "gallery.py"
CHROME = pathlib.Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
BREAK = "<script>document.querySelectorAll('[data-widget=\"chart\"]').forEach(function (f) { %s });</script></html>"


def run(edit=lambda page: page):
    with tempfile.TemporaryDirectory() as d:
        page = pathlib.Path(d) / "gallery.html"
        subprocess.run([sys.executable, str(GALLERY), str(page)], check=True)
        page.write_text(edit(page.read_text()))
        r = subprocess.run([sys.executable, str(CHECK), str(page)], capture_output=True, text=True)
        return r.returncode, r.stdout


def after_draw(js):
    return lambda page: page.replace("</html>", BREAK % js)


@unittest.skipUnless(CHROME.exists(), "no Chrome")
class ChartCheck(unittest.TestCase):
    def test_gallery_passes(self):
        code, out = run()
        self.assertEqual(code, 0, out)
        for kind in ("bar", "dot", "line", "spark", "scatter", "histogram", "box", "stacked", "heatmap"):
            self.assertIn(f"{kind} ", out)

    def test_bar_off_by_its_scale_fails(self):
        code, out = run(after_draw("if (f.dataset.chart === 'bar') { var m = f.querySelector('rect.mark'); m.setAttribute('width', +m.getAttribute('width') + 3); }"))
        self.assertEqual(code, 1)
        self.assertIn("bar", out)
        self.assertIn("width", out)

    def test_bar_not_from_zero_fails(self):
        code, out = run(after_draw("if (f.dataset.chart === 'bar') f.querySelectorAll('rect.mark').forEach(function (m) { m.setAttribute('x', +m.getAttribute('x') + 5); });"))
        self.assertEqual(code, 1)
        self.assertIn("x ", out)

    def test_heatmap_step_wrong_fails(self):
        code, out = run(after_draw("if (f.dataset.chart === 'heatmap') f.querySelector('rect.mark').setAttribute('class', 'mark s5');"))
        self.assertEqual(code, 1)
        self.assertIn("heatmap", out)

    def test_value_without_mark_fails(self):
        code, out = run(after_draw("if (f.dataset.chart === 'scatter') f.querySelector('circle.mark').remove();"))
        self.assertEqual(code, 1)
        self.assertIn("no mark", out)

    def test_mark_off_keyboard_path_fails(self):
        code, out = run(after_draw("if (f.dataset.chart === 'line') { var m = f.querySelectorAll('.mark')[2]; m.setAttribute('class', m.getAttribute('class').replace('mark', 'point')); }"))
        self.assertEqual(code, 1)
        self.assertIn("keyboard", out)

    def test_player_stuck_at_first_table_fails(self):
        stuck = "<script>document.addEventListener('click', function (e) { if (e.target.closest('.controls')) e.stopImmediatePropagation(); }, true);</script></html>"
        code, out = run(lambda page: page.replace("</html>", stuck))
        self.assertEqual(code, 1)
        self.assertIn("buttons player stands at table 1, not its last, 2", out)
        self.assertIn("scroll player stands at table 1, not its last, 3", out)

    def test_two_sentence_summary_fails(self):
        code, out = run(lambda page: page.replace("부산의 하루 요청이 가장 많아요.", "부산의 하루 요청이 가장 많아요. 광주가 가장 적어요.", 1))
        self.assertEqual(code, 1)
        self.assertIn("summary", out)


if __name__ == "__main__":
    unittest.main()

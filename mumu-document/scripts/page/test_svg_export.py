"""`svg-export.py` writes each figure of a page as a standalone SVG that renders on its own."""
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHECK = ROOT / "scripts" / "page" / "svg-export.py"
CHROME = pathlib.Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
PAGE = """<!doctype html><html lang="ko"><meta charset="utf-8"><title>그림</title>
<style>:root { color-scheme: light dark; --ink: light-dark(#1a1a1a, #eeeeee); --bg: light-dark(#ffffff, #111111); }
body { background: var(--bg); } .box { fill: none; stroke: var(--ink); stroke-width: 2; }
.label { fill: var(--ink); font: 14px sans-serif; } .edge { stroke: var(--ink); marker-end: url(#a-tip); }</style>
<main>
<figure><svg viewBox="0 0 280 80" width="280" height="80" role="img" aria-labelledby="a-t">
<title id="a-t">작업 흐름</title>
<defs><marker id="a-tip" viewBox="0 0 8 8" refX="8" refY="4" markerWidth="8" markerHeight="8" orient="auto"><path d="M0 0L8 4L0 8z"/></marker></defs>
<rect class="box" x="8" y="20" width="96" height="40"/><text class="label" x="20" y="44">큐</text>
<line class="edge" x1="104" y1="40" x2="176" y2="40"/>
<rect class="box" x="176" y="20" width="96" height="40"/><text class="label" x="188" y="44">작업자</text>
</svg></figure>
<figure><svg viewBox="0 0 80 80" width="80" height="80" role="img" aria-label="점"><circle class="box" cx="40" cy="40" r="20"/></svg></figure>
<svg width="12" height="12" aria-hidden="true"><circle cx="6" cy="6" r="4"/></svg>
</main></html>"""
FRAME = """<canvas id=c width=280 height=80></canvas><script>
var i = new Image(); i.onload = function () { var x = c.getContext('2d'); x.drawImage(i, 0, 0);
var d = x.getImageData(0, 0, 280, 80).data, n = 0; for (var k = 0; k < d.length; k += 4) if (d[k] < 128) n++;
document.body.dataset.r = i.naturalWidth + ' ' + n; }; i.onerror = function () { document.body.dataset.r = 'error'; };
i.src = 'data:image/svg+xml,' + encodeURIComponent(%s);</script>"""


def export(html):
    d = tempfile.mkdtemp()
    page = pathlib.Path(d) / "page.html"
    page.write_text(html)
    r = subprocess.run([sys.executable, str(CHECK), str(page), d], capture_output=True, text=True)
    return r, pathlib.Path(d)


def rendered(svg):
    """'<natural width> <dark pixels>' of an SVG drawn by Chrome as an image, alone."""
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(FRAME % repr(svg))
    out = subprocess.run([str(CHROME), "--headless", "--disable-gpu", "--dump-dom", "--virtual-time-budget=2000",
                          f"file://{f.name}"], capture_output=True, text=True).stdout
    return re.search(r'data-r="([^"]*)"', out).group(1)


@unittest.skipUnless(CHROME.exists(), "no Chrome")
class SvgExport(unittest.TestCase):
    def test_each_figure_is_written_and_decorations_skipped(self):
        r, d = export(PAGE)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(p.name for p in d.glob("*.svg")), ["page-1.svg", "page-2.svg"])
        self.assertIn("page-1.svg", r.stdout)

    def test_figure_is_standalone(self):
        svg = (export(PAGE)[1] / "page-1.svg").read_text()
        self.assertTrue(svg.startswith("<svg"), svg[:40])
        self.assertIn('xmlns="http://www.w3.org/2000/svg"', svg)
        self.assertNotRegex(svg, r"class=|var\(|light-dark")
        self.assertIn("url(#a-tip)", svg)

    def test_figure_renders_alone(self):
        width, dark = rendered((export(PAGE)[1] / "page-1.svg").read_text()).split()
        self.assertEqual(width, "280")
        self.assertGreater(int(dark), 200)

    def test_chart_svg_is_written(self):
        chart = '<figure data-widget="chart"><div class="plot"><svg role="group" viewBox="0 0 80 80" width="80" height="80"><rect class="box" x="8" y="8" width="40" height="40" role="img" aria-label="막대"/></svg></div></figure>'
        r, d = export(PAGE.replace("</main>", chart + "</main>"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("<rect", (d / "page-3.svg").read_text())

    def test_page_without_figures_fails(self):
        r, _ = export(PAGE.replace("<figure>", "<div hidden>").replace("</figure>", "</div>").replace('role="img"', ""))
        self.assertEqual(r.returncode, 1)
        self.assertIn("no figure", r.stdout)


if __name__ == "__main__":
    unittest.main()

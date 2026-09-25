"""`check.py` passes a good page and the gallery, and each rule fails the page that breaks it."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHECK, GALLERY = ROOT / "scripts" / "page" / "check.py", ROOT / "scripts" / "skill" / "gallery.py"
CHROME = pathlib.Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
GOOD = """<!doctype html><html lang="ko"><meta charset="utf-8"><title>작업 큐 구조</title>
<main><h1>작업 큐의 구조</h1>
<h2>저장소 <code>jobs.db</code></h2>
<p>큐(queue)는 <code>POST /jobs with a body</code>로 일을 받아요. 저장소는 SQLite입니다.</p>
<pre>git log --oneline main</pre>
<p><button popovertarget="h1">큐</button>에 일을 넣어요.</p><div id="h1" popover>일을 차례로 담아 두는 곳이에요.</div>
<svg width="280" height="80" viewBox="0 0 280 80"><title>흐름: 일 하나를 넣기</title>
<text x="8" y="24" font-size="14">작업자</text><text x="160" y="24" font-size="14">저장소</text></svg>
<div id="c"></div></main>
<script>document.getElementById('c').textContent = '다음';</script></html>"""
# (what to replace in GOOD, its replacement, a line the output must hold)
FAILS = [
    ('x="160"', 'x="24"', "labels 2"),
    ('x="160"', 'x="250"', "labels 1"),
    ('<div id="h1" popover>', '<div id="h1">', "hints 0/1"),
    (' lang="ko"', "", 'lang is "", not "ko"'),
    ("저장소는 SQLite입니다.", "the <strong>job</strong> store", "English: the job store"),
    ("'다음'", "'Play the steps'", "English: Play the steps"),
    ("흐름: 일 하나를 넣기", "Flow: add a job", "English: Flow: add a job"),
    ('<div id="c">', '<img alt="the job queue" src="x.png"><div id="c">', "English: the job queue"),
    ("SQLite입니다.", "SQLite이다.", "plain ending: 저장소는 SQLite이다."),
    ("<h1>작업 큐의 구조</h1>", "<h1>큐가 일을 받습니다</h1>", "sentence heading: 큐가 일을 받습니다"),
]
BREAK = "<script>document.querySelectorAll('[data-widget=\"chart\"]').forEach(function (f) { %s });</script></html>"
CHART_FAILS = [
    ("if (f.dataset.chart === 'bar') { var m = f.querySelector('rect.mark'); m.setAttribute('width', +m.getAttribute('width') + 3); }", "width"),
    ("if (f.dataset.chart === 'scatter') f.querySelector('circle.mark').remove();", "no mark"),
    ("if (f.dataset.chart === 'line') { var m = f.querySelectorAll('.mark')[2]; m.setAttribute('class', 'point'); }", "keyboard"),
]
STUCK = "<script>document.addEventListener('click', function (e) { if (e.target.closest('.controls')) e.stopImmediatePropagation(); }, true);</script></html>"


def run(html):
    with tempfile.TemporaryDirectory() as d:
        page = pathlib.Path(d) / "page.html"
        page.write_text(html)
        r = subprocess.run([sys.executable, str(CHECK), str(page)], capture_output=True, text=True)
        return r.returncode, r.stdout


@unittest.skipUnless(CHROME.exists(), "no Chrome")
class Check(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable, str(GALLERY), f"{d}/g.html"], check=True)
            cls.gallery = pathlib.Path(f"{d}/g.html").read_text()

    def test_good_page_passes(self):
        code, out = run(GOOD)
        self.assertEqual((code, out.splitlines()[-1]), (0, "pass"), out)

    def test_each_rule_fails(self):
        for old, new, line in FAILS:
            with self.subTest(line):
                self.assertIn(old, GOOD)
                code, out = run(GOOD.replace(old, new))
                self.assertEqual(code, 1, out)
                self.assertIn(line, out)

    def test_gallery_passes(self):
        code, out = run(self.gallery)
        self.assertEqual(code, 0, out)
        for kind in ("bar", "dot", "line", "spark", "scatter", "histogram", "box", "stacked", "heatmap"):
            self.assertIn(f" {kind} marks", out)

    def test_each_chart_rule_fails(self):
        for js, word in CHART_FAILS + [(None, "slide stands at table 1, not its last, 2")]:
            with self.subTest(word):
                code, out = run(self.gallery.replace("</html>", STUCK if js is None else BREAK % js))
                self.assertEqual(code, 1, out)
                self.assertIn(word, out)

    def test_swipe_that_does_not_react_fails(self):
        dead = "<script>window.IntersectionObserver = function () { this.observe = function () {}; };</script><style>"
        code, out = run(self.gallery.replace("<style>", dead, 1))
        self.assertEqual(code, 1, out)
        self.assertIn("swipe 1 step 1/3 FAIL", out)


if __name__ == "__main__":
    unittest.main()

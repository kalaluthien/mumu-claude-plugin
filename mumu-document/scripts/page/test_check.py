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
<svg width="280" height="80" viewBox="0 0 280 80"><title>흐름: 일 하나를 넣기</title>
<text x="8" y="24" font-size="14">작업자</text><text x="160" y="24" font-size="14">저장소</text></svg>
<div id="c"></div></main>
<script>document.getElementById('c').textContent = '다음';</script></html>"""
# (what to replace in GOOD, its replacement, a line the output must hold)
FAILS = [
    ('x="160"', 'x="24"', "labels 2"),
    ('x="160"', 'x="250"', "labels 1"),
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
    ("if (f.dataset.chart === 'line') f.querySelector('circle.mark').remove();", "no mark"),
    ("if (f.dataset.chart === 'line') { var m = f.querySelector('circle.mark'); m.setAttribute('cy', +m.getAttribute('cy') + 3); }", "cy"),
    ("if (f.dataset.chart === 'bar') { var m = f.querySelector('rect.mark'); var s = f.querySelector('svg'), a = s.dataset.x.split(' '); a[1] = 1; s.dataset.x = a.join(' '); }", "does not span"),
]
FOUR = "".join(f'<h2 id="s{i}">부분 {i}</h2><p>내용이에요.</p>' for i in range(1, 5))
NAV = '<nav><ol>' + "".join(f'<li><a href="#s{i}">부분 {i}</a></li>' for i in range(1, 5)) + '</ol></nav>'
PART = (ROOT / "skills" / "writing-documents" / "references" / "artifact" / "shared" / "chapters.html").read_text()
CHAPTERS = ('<nav><ol>' + "".join(f'<li><a href="#c{i}">장 {i}</a></li>' for i in range(1, 4)) + '</ol></nav>'
            + "".join(f'<section data-chapter><h2 id="c{i}">장 {i}</h2><p>내용이에요.</p><h3 id="c{i}-a">절 {i}</h3>'
                      f'<p><dfn id="t{i}">용어 {i}</dfn>를 정의해요. <a href="#t{(i % 3) + 1}">다음 용어</a>를 봐요.</p></section>'
                      for i in range(1, 4)))
PAGED = GOOD.replace('<h2>저장소 <code>jobs.db</code></h2>', CHAPTERS).replace("</html>", PART + "</html>")
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

    def test_contents_at_four_h2s(self):
        page = GOOD.replace('<h2>저장소 <code>jobs.db</code></h2>', FOUR)
        code, out = run(page)
        self.assertEqual(code, 1, out)
        self.assertIn("contents 4 h2 0 linked FAIL", out)
        code, out = run(page.replace("<h1>작업 큐의 구조</h1>", "<h1>작업 큐의 구조</h1>" + NAV))
        self.assertEqual(code, 0, out)
        self.assertIn("contents 4 h2 4 linked nav pass", out)

    def test_no_contents_under_four_h2s(self):
        code, out = run(GOOD.replace("<h1>작업 큐의 구조</h1>", "<h1>작업 큐의 구조</h1>" + NAV))
        self.assertEqual(code, 1, out)
        self.assertIn("contents 1 h2 0 linked nav FAIL", out)

    def test_chapter_page_passes(self):
        code, out = run(PAGED)
        self.assertEqual(code, 0, out)
        self.assertIn("chapters 3 load 10/10 nav 3/3 pager 4/4 back 1/1 pass", out)

    def test_each_chapter_rule_fails(self):
        for old, new, line in [
            ("addEventListener('hashchange', show);", "", "nav link #c2 shows chapters [1], not 2"),
            ("c.hidden = c !== at;", "", "a load with no #id shows chapters [1, 2, 3], not 1"),
            ('<section data-chapter><h2 id="c3">', '<h2 id="c3">', "1 h3 outside a chapter"),
            ('<a href="#t2">', '<a href="#x">', "links #x has no target FAIL"),
        ]:
            with self.subTest(line):
                self.assertIn(old, PAGED)
                code, out = run(PAGED.replace(old, new))
                self.assertEqual(code, 1, out)
                self.assertIn(line, out)

    def test_nested_page_without_chapters_fails(self):
        code, out = run(GOOD.replace("</p>", '</p><h3 id="x">절</h3><p><a href="#x">절</a>로 가요.</p>', 1))
        self.assertEqual(code, 1, out)
        self.assertIn("chapters 0 FAIL: 1 h3 outside a chapter", out)

    def test_gallery_passes(self):
        code, out = run(self.gallery)
        self.assertEqual(code, 0, out)
        for kind in ("bar", "line"):
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

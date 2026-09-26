"""The skill's scripts: each passes the real skill and a good page, and each check fails the copy that breaks it.

Run: uvx --with playwright pytest mumu-document/tests -q
"""
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "writing-documents"
REFS = SKILL / "references"
CHECK, SKILL_CHECK = SKILL / "scripts" / "check.py", SKILL / "scripts" / "skill-check.py"
CHROME = pathlib.Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

# The gallery: every widget in every state, light and dark, in a .theme-* box with data-state set, which the skin and
# the widgets read to force that state; the chart shows each fixture below by default and the first in every state.
STATES = ("default", "hover", "focus", "open", "disabled")
KOREAN = {"Back|Next": "뒤로|다음", "gone": "삭제", "changed": "변경", "new": "추가", "Data table": "데이터 표",
          "caller kind|callee kind": "사람|외부 시스템"}
FIXTURES = {"chart": """<figure data-widget="chart" data-chart="bar">
  <figcaption>부산의 하루 요청이 가장 많아요.</figcaption>
  <div class="plot"></div>
  <details><summary>표로 보기</summary><div class="scroll"><table>
    <thead><tr><th scope="col">도시</th><th scope="col">하루 요청(건)</th></tr></thead>
    <tbody>
      <tr><th scope="row">서울</th><td>1,240</td></tr>
      <tr data-note="지난달 두 배"><th scope="row">부산</th><td>1,870</td></tr>
      <tr><th scope="row">대구</th><td>620</td></tr>
      <tr><th scope="row">광주</th><td>95</td></tr>
    </tbody>
  </table></div></details>
</figure>
<figure data-widget="chart" data-chart="line">
  <figcaption>2022년부터 모바일 사용자가 웹 사용자보다 많아요.</figcaption>
  <div class="plot"></div>
  <details><summary>표로 보기</summary><div class="scroll"><table>
    <thead><tr><th scope="col">연도</th><th scope="col">웹</th><th scope="col">모바일</th><th scope="col">데스크톱 앱</th></tr></thead>
    <tbody>
      <tr><th scope="row">2019</th><td>52</td><td>21</td><td>12</td></tr>
      <tr><th scope="row">2020</th><td>50</td><td>30</td><td>13</td></tr>
      <tr><th scope="row">2021</th><td>47</td><td>41</td><td>15</td></tr>
      <tr data-note="새 앱 출시"><th scope="row">2022</th><td>45</td><td>55</td><td>14</td></tr>
      <tr><th scope="row">2023</th><td>44</td><td>63</td><td>16</td></tr>
    </tbody>
  </table></div></details>
</figure>
<figure data-widget="chart" data-chart="bar" data-slide data-labels="뒤로|다음">
  <figcaption>1년 사이 부산의 요청이 서울을 앞질렀어요.</figcaption>
  <div class="plot"></div>
  <ol class="steps">
    <li>작년에는 서울의 요청이 가장 많았어요.</li>
    <li>올해는 부산의 요청이 서울보다 많아졌어요.</li>
  </ol>
  <details><summary>표로 보기</summary><div class="scroll">
    <table><caption>작년</caption>
      <thead><tr><th scope="col">도시</th><th scope="col">하루 요청(건)</th></tr></thead>
      <tbody><tr><th scope="row">서울</th><td>1,100</td></tr><tr><th scope="row">부산</th><td>700</td></tr><tr><th scope="row">대구</th><td>540</td></tr></tbody>
    </table>
    <table><caption>올해</caption>
      <thead><tr><th scope="col">도시</th><th scope="col">하루 요청(건)</th></tr></thead>
      <tbody><tr><th scope="row">서울</th><td>1,240</td></tr><tr><th scope="row">부산</th><td>1,870</td></tr><tr><th scope="row">대구</th><td>620</td></tr></tbody>
    </table>
  </div></details>
</figure>
<figure data-widget="chart" data-chart="line" data-slide data-labels="뒤로|다음">
  <figcaption>배포를 나눌수록 실패가 줄었어요.</figcaption>
  <div class="plot"></div>
  <ol class="steps">
    <li>한 번에 배포할 때는 실패가 잦았어요.</li>
    <li>두 번으로 나누자 실패가 줄었어요.</li>
    <li>네 번으로 나누자 실패가 거의 없어졌어요.</li>
  </ol>
  <details><summary>표로 보기</summary><div class="scroll">
    <table><caption>한 번에 배포</caption>
      <thead><tr><th scope="col">주</th><th scope="col">실패(건)</th></tr></thead>
      <tbody><tr><th scope="row">1주</th><td>9</td></tr><tr><th scope="row">2주</th><td>11</td></tr><tr><th scope="row">3주</th><td>8</td></tr><tr><th scope="row">4주</th><td>10</td></tr></tbody>
    </table>
    <table><caption>두 번으로 나눔</caption>
      <thead><tr><th scope="col">주</th><th scope="col">실패(건)</th></tr></thead>
      <tbody><tr><th scope="row">1주</th><td>6</td></tr><tr><th scope="row">2주</th><td>5</td></tr><tr><th scope="row">3주</th><td>4</td></tr><tr><th scope="row">4주</th><td>4</td></tr></tbody>
    </table>
    <table><caption>네 번으로 나눔</caption>
      <thead><tr><th scope="col">주</th><th scope="col">실패(건)</th></tr></thead>
      <tbody><tr><th scope="row">1주</th><td>2</td></tr><tr><th scope="row">2주</th><td>1</td></tr><tr><th scope="row">3주</th><td>1</td></tr><tr><th scope="row">4주</th><td>0</td></tr></tbody>
    </table>
  </div></details>
</figure>"""}


def parts(html):
    """(style and script blocks, body) of a unit, its spec comment dropped."""
    html = re.sub(r"^<!--.*?-->\s*", "", html, count=1, flags=re.S)
    blocks = re.findall(r"<style[^>]*>.*?</style>|<script>.*?</script>", html, re.S)
    return blocks, re.sub(r"<style[^>]*>.*?</style>\s*|<script>.*?</script>\s*", "", html, flags=re.S)


def in_state(body, state):
    if state == "open":
        body = body.replace("<details>", "<details open>").replace(" hidden>", ">")
    if state == "disabled":
        body = re.sub(r"<(button|textarea|fieldset)\b", r"<\1 disabled", body)
    return re.sub(r"\{\{([^}]*)\}\}", lambda m: KOREAN.get(m.group(1), "예시"), body)


def gallery():
    head, sections = [], []
    for f in sorted(REFS.glob("*.html")):
        if f.stem == "page":
            continue
        blocks, body = parts(f.read_text())
        head += blocks
        if f.stem in FIXTURES:
            bodies, full = re.split(r"\n(?=<figure)", FIXTURES[f.stem].strip()), 1
        else:
            bodies = re.split(r"\n(?=<section)", body.strip())
            full = len(bodies)
        copies = [f'<div class="theme-{mode}" data-state="{state}">\n<p class="muted"><code>{f.stem}</code> 예시</p>\n'
                  f'{in_state(one.replace("{{id}}", f"{f.stem}-{mode}-{state}-{n}"), state)}</div>'
                  for mode in ("light", "dark") for n, one in enumerate(bodies) for state in (STATES if n < full else STATES[:1])]
        sections.append(f'<section><h2 id="g-{f.stem}"><code>{f.stem}</code></h2>\n' + "\n".join(copies) + "\n</section>")
    shell = (REFS / "page.html").read_text()
    head += parts(shell)[0]
    nav = "<nav><ol>" + "".join(f'<li><a href="#{i}">{re.sub(r"<[^>]+>", "", text).strip()}</a></li>'
                                for i, text in re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', "".join(sections), re.S)) + "</ol></nav>"
    return ('<!doctype html>\n<html lang="ko">\n<meta charset="utf-8">\n<title>위젯 모음</title>\n'
            + "\n".join(b for b in head if b.startswith("<style"))
            + "\n<main>\n<h1>위젯 모음</h1>\n" + nav + "\n".join(sections) + "\n</main>\n"
            + "\n".join(b for b in head if b.startswith("<script")) + "\n</html>\n")


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
    ("<pre>git log --oneline main</pre>", "<pre>요청 → 큐 → 작업자</pre>", "no use-case for '요청 → 큐 → 작업자'"),
    ("SQLite입니다.", "SQLite입니다. <code>api/</code>, <code>queue.py</code>, <code>worker.py:12</code>를 거쳐요.",
     "no file-tree for jobs.db, api/, queue.py, worker.py"),
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
PART = "\n".join(parts((REFS / "page.html").read_text())[0])
CHAPTERS = ('<nav><ol>' + "".join(f'<li><a href="#c{i}">장 {i}</a></li>' for i in range(1, 4)) + '</ol></nav>'
            + "".join(f'<section data-chapter><h2 id="c{i}">장 {i}</h2><p>내용이에요.</p><h3 id="c{i}-a">절 {i}</h3>'
                      f'<p><dfn id="t{i}">용어 {i}</dfn>를 정의해요. <a href="#t{(i % 3) + 1}">다음 용어</a>를 봐요.</p></section>'
                      for i in range(1, 4)))
PAGED = GOOD.replace('<h2>저장소 <code>jobs.db</code></h2>', CHAPTERS).replace("</html>", PART + "</html>")
REPORT = GOOD.replace("<pre>git log --oneline main</pre>", '<div class="scroll"><table><thead><tr><th>도시</th><th>요청(건)</th></tr></thead>'
                      '<tbody><tr><td>서울</td><td>1,240</td></tr><tr><td>부산</td><td>1,870</td></tr></tbody></table></div>')


def dream(name):
    """A fixture page of `pages/<name>.html`'s main in the skin, with the diagram widget's style."""
    shell = re.sub(r"^<!--.*?-->\s*", "", (REFS / "page.html").read_text(), flags=re.S).replace("{{title}}", "dream 스킬 설계안")
    style = "\n".join(b for b in parts((REFS / "diagram.html").read_text())[0] if b.startswith("<style"))
    main = (ROOT / "tests" / "pages" / f"{name}.html").read_text().strip()
    return re.sub(r"<main>.*?</main>", lambda m: style + "\n" + main, shell, flags=re.S)


STUCK = "<script>document.addEventListener('click', function (e) { if (e.target.closest('.controls')) e.stopImmediatePropagation(); }, true);</script></html>"


def check(html):
    with tempfile.TemporaryDirectory() as d:
        page = pathlib.Path(d) / "page.html"
        page.write_text(html)
        r = subprocess.run([sys.executable, str(CHECK), str(page)], capture_output=True, text=True)
        return r.returncode, r.stdout


@unittest.skipUnless(CHROME.exists(), "no Chrome")
class Check(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gallery = gallery()

    def test_good_page_passes(self):
        code, out = check(GOOD)
        self.assertEqual((code, out.splitlines()[-1]), (0, "pass"), out)

    def test_each_rule_fails(self):
        for old, new, line in FAILS:
            with self.subTest(line):
                self.assertIn(old, GOOD)
                code, out = check(GOOD.replace(old, new))
                self.assertEqual(code, 1, out)
                self.assertIn(line, out)

    def test_page_that_skips_mapping_widgets_fails(self):
        code, out = check(dream("dream"))
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"mapping 8 files 1 flows FAIL: no file-tree for .*; no use-case for '/dream ")

    def test_page_with_mapping_widgets_passes(self):
        code, out = check(dream("dream-drawn"))
        self.assertEqual((code, out.splitlines()[-1]), (0, "pass"), out)
        self.assertIn("mapping 8 files 0 flows pass", out)

    def test_plain_report_needs_no_widget(self):
        code, out = check(REPORT)
        self.assertEqual((code, out.splitlines()[-1]), (0, "pass"), out)
        self.assertIn("mapping 1 files 0 flows pass", out)

    def test_contents_at_four_h2s(self):
        page = GOOD.replace('<h2>저장소 <code>jobs.db</code></h2>', FOUR)
        code, out = check(page)
        self.assertEqual(code, 1, out)
        self.assertIn("contents 4 h2 0 linked FAIL", out)
        code, out = check(page.replace("<h1>작업 큐의 구조</h1>", "<h1>작업 큐의 구조</h1>" + NAV))
        self.assertEqual(code, 0, out)
        self.assertIn("contents 4 h2 4 linked nav pass", out)

    def test_no_contents_under_four_h2s(self):
        code, out = check(GOOD.replace("<h1>작업 큐의 구조</h1>", "<h1>작업 큐의 구조</h1>" + NAV))
        self.assertEqual(code, 1, out)
        self.assertIn("contents 1 h2 0 linked nav FAIL", out)

    def test_chapter_page_passes(self):
        code, out = check(PAGED)
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
                code, out = check(PAGED.replace(old, new))
                self.assertEqual(code, 1, out)
                self.assertIn(line, out)

    def test_nested_page_without_chapters_fails(self):
        code, out = check(GOOD.replace("</p>", '</p><h3 id="x">절</h3><p><a href="#x">절</a>로 가요.</p>', 1))
        self.assertEqual(code, 1, out)
        self.assertIn("chapters 0 FAIL: 1 h3 outside a chapter", out)

    def test_gallery_passes(self):
        code, out = check(self.gallery)
        self.assertEqual(code, 0, out)
        for kind in ("bar", "line"):
            self.assertIn(f" {kind} marks", out)

    def test_each_chart_rule_fails(self):
        for js, word in CHART_FAILS + [(None, "slide stands at table 1, not its last, 2")]:
            with self.subTest(word):
                code, out = check(self.gallery.replace("</html>", STUCK if js is None else BREAK % js))
                self.assertEqual(code, 1, out)
                self.assertIn(word, out)

    def test_swipe_that_does_not_react_fails(self):
        dead = "<script>window.IntersectionObserver = function () { this.observe = function () {}; };</script><style>"
        code, out = check(self.gallery.replace("<style>", dead, 1))
        self.assertEqual(code, 1, out)
        self.assertIn("swipe 1 step 1/3 FAIL", out)




W, SKIN = "references/", "references/page.html"
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
    (W + "diagram.html", [("--diagram-indent: var(--sp-4)", "--diagram-indent: var(--sp-9)")], r"token --sp-9 is not in the skin"),
    (W + "diagram.html", [("--diagram-indent: var(--sp-4)", "--diagram-indent: var(--p-white)")], r"reads primitive --p-white"),
    (W + "diagram.html", [("--diagram-indent: var(--sp-4);", "--diagram-indent: var(--sp-4); --diagram-x: var(--sp-1);")], None),
    (SKIN, [("flex: 0 0 85%;", "flex: 0 0 20rem;")], r"literal size: 20rem"),
    (SKIN, [("light-dark(#d55e00,", "light-dark(#f5c9a8,")], r"--kind-2 on --fill light"),
    (SKIN, [("--p-grey-500: #757575", "--p-grey-500: #c0c0c0")], r"--muted on --bg light"),
    (SKIN, [("#8a8a8a", "#3a3d42")], r"--border on --fill dark"),
    (SKIN, [("#057dbc", "#7fc4ea")], r"--link on --bg light"),
    (SKIN, [("  --accent:", "  --link:")], r"no role --accent"),
    # sky blue and lavender stay apart to a normal eye and pass 3:1 on black, but merge for a deuteranope
    (SKIN, [("light-dark(#cc79a7, #cc79a7)", "light-dark(#cc79a7, #a9a0e8)")],
     r"(?s)^(?!.*normal).*--kind-1 and --kind-4 dark deuteranopia ΔE \d+\.\d < 10"),
]


def skill_check(skill):
    r = subprocess.run([sys.executable, str(SKILL_CHECK), str(skill)], capture_output=True, text=True)
    return r.returncode, r.stdout


class SkillCheck(unittest.TestCase):
    def test_real_skill_passes(self):
        self.assertEqual(skill_check(SKILL), (0, "pass\n"))

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
                code, out = skill_check(skill)
                if want is None:
                    self.assertEqual((code, out), (0, "pass\n"))
                else:
                    self.assertEqual(code, 1, out)
                    self.assertRegex(out, want)




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
    r = subprocess.run([sys.executable, str(CHECK), str(page), "--svg", d], capture_output=True, text=True)
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

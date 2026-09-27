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
ASSEMBLE = SKILL / "scripts" / "assemble.py"
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
</figure>""",
            "filter": """<div data-widget="filter" data-for="{{id}}" data-unit="개">
  <div role="group" data-facet="kind" aria-label="갈래">
    <button type="button" data-tag="">전체</button><button type="button" data-tag="빛">빛</button><button type="button" data-tag="색">색</button>
  </div>
  <input type="search" aria-label="주제에서 찾기" placeholder="찾을 말">
  <output aria-live="polite"></output>
</div>
<ul id="{{id}}"><li data-kind="빛">창가의 빛</li><li data-kind="빛">역광</li><li data-kind="색">피부색</li></ul>""",
            "controls": """<figure data-widget="controls" data-split="처음|지금">
  <figcaption>크기를 바꾸며 원을 봐요.</figcaption>
  <div class="stage"><svg viewBox="0 0 120 80" role="img" aria-label="원"><circle cx="60" cy="40" style="r: calc(var(--size, 20) * 1px)"/></svg></div>
  <div class="panel">
    <label>크기 <input type="range" name="size" min="10" max="30" value="20"><output data-unit="px"></output></label>
    <div role="group" data-name="size2" aria-label="두 배">
      <button type="button" data-value="1">한 배</button><button type="button" data-value="2">두 배</button>
    </div>
    <div class="presets"><button type="button" data-preset="size=30">크게</button></div>
    <p>넓이 <output data-calc="3 * size * size * size2" data-digits="0"></output></p>
  </div>
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
            bodies, full = re.split(r"\n(?=<figure|<div data-widget)", FIXTURES[f.stem].strip()), 1
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


GOOD = """<!doctype html><html lang="ko"><meta charset="utf-8"><title>작업 큐 구조</title><style id="skin"></style>
<main><h1>작업 큐의 구조</h1>
<p class="read">큐는 일을 저장소에 쌓고, 작업자가 하나씩 꺼내 가요.</p>
<h2>저장소 <code>jobs.db</code></h2>
<p>큐(queue)는 <code>POST /jobs with a body</code>로 일을 받아요. 저장소는 SQLite입니다.</p>
<pre>git log --oneline main</pre>
<div data-widget="diagram" data-diagram="system-context"><svg width="280" height="80" viewBox="0 0 280 80"><title>흐름: 일 하나를 넣기</title>
<text x="8" y="24" font-size="14">작업자</text><text x="160" y="24" font-size="14">저장소</text></svg></div>
<div id="c"></div></main>
<script>document.getElementById('c').textContent = '다음';</script></html>"""
ANSWER = '<p class="read">큐는 일을 저장소에 쌓고, 작업자가 하나씩 꺼내 가요.</p>'
FIGURE = ('<div data-widget="diagram" data-diagram="system-context"><svg width="280" height="80" viewBox="0 0 280 80">'
          '<title>흐름: 일 하나를 꺼내기</title><text x="8" y="24" font-size="14">큐</text></svg></div>')
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
    ("<title>작업 큐 구조</title>", "<title>{{title}}</title>", "shell FAIL: {{title}} left"),
    ('<style id="skin"></style>', "", 'shell FAIL: no <style id="skin">'),
    ("<h1>작업 큐의 구조</h1>", "<p>작업 큐의 구조</p>", "shell FAIL: no h1"),
    ("SQLite입니다.", "SQLite입니다. 요청 -&gt; 큐로 가요.", "korean ASCII arrow: Lite입니다. 요청 -> 큐로 가요. FAIL"),
    ("SQLite입니다.", "SQLite입니다. 요청 =&gt; 큐로 가요.", "korean ASCII arrow: Lite입니다. 요청 => 큐로 가요. FAIL"),
    ('<div data-widget="diagram" data-diagram="system-context">', "<div>", "1 hand-drawn figure outside a widget"),
    ("SQLite입니다.", "좋은 솔루션이다", "plain ending: 저장소는 좋은 솔루션이다 FAIL"),
    ("SQLite입니다.", "좋은 솔루션이다.", "plain ending: 저장소는 좋은 솔루션이다."),
    ("SQLite입니다.", "확인했음", "plain ending: 저장소는 확인했음 FAIL"),
    ("SQLite입니다.", "확인이 필요함.", "plain ending: 저장소는 확인이 필요함."),
    ('<div id="c">', '<div id="c" style="width:600px">', "FAIL: widest main > div#c"),
]
# (what to replace in GOOD, its replacement, a word no line may hold): each passes
PASSES = [
    ("SQLite입니다.", "SQLite입니다. <code>a -&gt; b</code>로 써요.", "arrow"),
    ("SQLite입니다.", "바다.", "plain ending"),
    ("SQLite입니다.", "마음이에요.", "plain ending"),
    ("SQLite입니다.", "4.00점이에요.", "plain ending"),
]
# after the charts draw, which waits for the page to parse
BREAK = ("<script>addEventListener('DOMContentLoaded', function () {"
         " document.querySelectorAll('[data-widget=\"chart\"]').forEach(function (f) { %s }); });</script></html>")
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


def widget_check(html):
    """check() of the gallery, which holds every widget in every state and so is no composed page: its composition
    line must fail on its widget count, and the code is that of every other line."""
    code, out = check(html)
    lines = out.splitlines()[:-1]
    assert any(re.match(r"composition .*FAIL: .*widgets on the page, over", l) for l in lines), out
    return int(any("FAIL" in l for l in lines if not l.startswith("composition "))), out


@unittest.skipUnless(CHROME.exists(), "no Chrome")
class Check(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gallery = gallery()

    def test_good_page_passes(self):
        code, out = check(GOOD)
        self.assertEqual((code, out.splitlines()[-1]), (0, "pass"), out)
        self.assertNotRegex(out, r"\{\{|hand-drawn|arrow")

    def test_each_near_miss_passes(self):
        for old, new, word in PASSES:
            with self.subTest(new):
                self.assertIn(old, GOOD)
                code, out = check(GOOD.replace(old, new))
                self.assertEqual((code, out.splitlines()[-1]), (0, "pass"), out)
                self.assertNotIn(word, out)

    def test_empty_page_fails(self):
        code, out = check(GOOD.split("<main>")[0] + "<main>\n</main></html>")
        self.assertEqual((code, out.splitlines()), (1, ["empty", "FAIL"]), out)

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

    def test_page_without_answer_fails(self):
        for lead in ("", '<p class="read">큐의 구조</p>', "<p>큐의 구조를 봐요.</p>"):
            with self.subTest(lead):
                code, out = check(GOOD.replace(ANSWER, lead))
                self.assertEqual(code, 0 if lead.endswith("요.</p>") else 1, out)
                self.assertIn("composition 1 sentences before h2 1 widgets pass" if lead.endswith("요.</p>")
                              else "composition 0 sentences before h2 1 widgets FAIL: no sentence of the answer", out)

    def test_widgets_over_limit_fail(self):
        code, out = check(GOOD.replace("</svg></div>", "</svg></div>" + FIGURE))
        self.assertEqual(code, 1, out)
        self.assertIn("composition 1 sentences before h2 2 widgets FAIL: 2 widgets under '저장소 jobs.db', over 1", out)
        code, out = check(GOOD.replace("</svg></div>", '</svg></div><h2 id="s1">두 번째 그림</h2>' + FIGURE))
        self.assertEqual(code, 0, out)
        self.assertIn("composition 1 sentences before h2 2 widgets pass", out)
        for n, code in ((5, 0), (6, 1)):
            with self.subTest(n):
                sections = "".join(f'<h2 id="s{i}">그림 <code>{i}</code></h2>{FIGURE}' for i in range(n))
                nav = '<nav><ol>' + "".join(f'<li><a href="#s{i}">그림 {i}</a></li>' for i in range(n)) + '</ol></nav>'
                page = re.sub(r"<h2>.*</svg></div>", lambda m: nav + sections, GOOD, flags=re.S)
                got, out = check(page)
                self.assertEqual(got, code, out)
                self.assertIn(f"composition 1 sentences before h2 {n} widgets "
                              + ("pass" if code == 0 else "FAIL: 6 widgets on the page, over 5"), out)

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
        self.assertIn("chapters 3 load 10/10 nav 6/6 pager 4/4 back 1/1 pass", out)

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
        code, out = widget_check(self.gallery)
        self.assertEqual(code, 0, out)
        for kind in ("bar", "line"):
            self.assertIn(f" {kind} marks", out)
        self.assertIn("swipe 1 token in view 3/3 pass", out)
        self.assertRegex(out, r"clicks (\d+)/\1 pass")

    def test_each_chart_rule_fails(self):
        for js, word in CHART_FAILS + [(None, "slide stands at table 1, not its last, 2")]:
            with self.subTest(word):
                code, out = widget_check(self.gallery.replace("</html>", STUCK if js is None else BREAK % js))
                self.assertEqual(code, 1, out)
                self.assertIn(word, out)

    def test_chart_summary_splits_at_marks_not_decimals(self):
        said = "부산의 하루 요청이 가장 많아요."
        self.assertIn(said, self.gallery)
        code, out = widget_check(self.gallery.replace(said, "부산의 평균이 4.00점이에요."))
        self.assertEqual(code, 0, out)
        code, out = widget_check(self.gallery.replace(said, "부산이 많아요. 대구는 적어요."))
        self.assertEqual(code, 1, out)
        self.assertIn("summary is not one sentence", out)

    def test_swipe_that_does_not_react_fails(self):
        dead = "<script>window.IntersectionObserver = function () { this.observe = function () {}; };</script><style>"
        code, out = widget_check(self.gallery.replace("<style>", dead, 1))
        self.assertEqual(code, 1, out)
        self.assertIn("swipe 1 step 1/3 FAIL", out)

    def test_token_out_of_view_fails(self):
        # step 2's card sends the token past the stage's scroll width
        self.assertIn('data-x="444"', self.gallery)
        code, out = widget_check(self.gallery.replace('data-x="444"', 'data-x="1400"'))
        self.assertEqual(code, 1, out)
        self.assertIn("swipe 1 token in view 2/3 FAIL: steps 2", out)



# (what to replace in the assembled widgets page, its replacement, a line the output must hold)
BROKEN = [
    ('<div role="group" data-name="tone"', '<label>안 쓰는 값 <input type="range" name="unused" min="0" max="10" value="5">'
     '<output></output></label><div role="group" data-name="tone"', "controls 1 slider unused changes nothing"),
    ('data-preset="size=12 light=20 tone=cool"', 'data-preset="sise=12"', "controls 1 preset 작고 어둡게 changes nothing"),
    ("<main>", "<style>main nav.drawer.open { visibility: hidden; }</style><main>", "contents button changes nothing"),
    ("<main>", "<script>addEventListener('click', function (e) { if (e.target.closest('.top')) e.stopImmediatePropagation(); }, true);"
     "</script><main>", "top button changes nothing"),
    ("<main>", "<script>history.back = function () {};</script><main>", "back button returns to"),
    ("<main>", "<style>.flash { animation: none; }</style><main>", "does not flash its target"),
    ("<main>", "<script>addEventListener('input', function (e) { if (e.target.type === 'search') e.stopImmediatePropagation(); },"
     " true);</script><main>", "filter 1 search box changes nothing"),
    ('data-tag="빛"', 'data-tag=""', "filter 2 갈래 빛 changes nothing"),
]


def widgets_page():
    """tests/pages/widgets.html's body assembled into a page."""
    with tempfile.TemporaryDirectory() as d:
        page = pathlib.Path(d) / "page.html"
        subprocess.run([sys.executable, str(ASSEMBLE), str(ROOT / "tests" / "pages" / "widgets.html"), str(page)], check=True,
                       capture_output=True)
        return page.read_text()


@unittest.skipUnless(CHROME.exists(), "no Chrome")
class Widgets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = widgets_page()

    def test_page_with_every_new_part_passes(self):
        code, out = check(self.page)
        self.assertEqual((code, out.splitlines()[-1]), (0, "pass"), out)
        self.assertIn("layout motion 305/305", out)
        self.assertIn("clicks 24/24 pass", out)

    def test_each_broken_control_fails(self):
        for old, new, line in BROKEN:
            with self.subTest(line):
                self.assertIn(old, self.page)
                code, out = check(self.page.replace(old, new, 1))
                self.assertEqual(code, 1, out)
                self.assertIn(line, out)


def assemble(*args):
    return subprocess.run([sys.executable, str(ASSEMBLE), *args], capture_output=True, text=True)


# two charts filled, as an author writes the body
TWO_CHARTS = ('<h1>도시별 요청</h1>\n<p class="read">부산의 요청이 가장 많아요.</p>\n' + "".join(
    f'<section aria-labelledby="s{i}"><h2 id="s{i}">요청 {i + 1}</h2>\n{f}\n</section>\n'
    for i, f in enumerate(re.split(r"\n(?=<figure)", FIXTURES["chart"].strip())[:2])))


class Assemble(unittest.TestCase):
    def test_each_spec_is_small_and_unstyled(self):
        for widget in ("page", "chart", "filter", "controls", "file-tree", "system-context", "use-case"):
            with self.subTest(widget):
                r = assemble("--spec", widget)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertLessEqual(len(r.stdout.encode()), 4096)
                self.assertNotRegex(r.stdout, r"<style|<script")
                self.assertIn("{{", r.stdout)

    def test_unknown_widget_is_named(self):
        self.assertEqual(assemble("--spec", "sankey").returncode, 2)
        with tempfile.TemporaryDirectory() as d:
            body, page = pathlib.Path(d) / "body.html", pathlib.Path(d) / "page.html"
            body.write_text(TWO_CHARTS.replace('data-widget="chart"', 'data-widget="sankey"', 1))
            r = assemble(str(body), str(page))
            self.assertEqual(r.returncode, 2)
            self.assertIn("'sankey'", r.stderr)
            body.write_text(TWO_CHARTS + '<div data-widget="diagram" data-diagram="mind-map"></div>')
            r = assemble(str(body), str(page))
            self.assertEqual(r.returncode, 2)
            self.assertIn("'mind-map'", r.stderr)
            self.assertFalse(page.exists())

    @unittest.skipUnless(CHROME.exists(), "no Chrome")
    def test_assembled_page_passes_with_each_script_once(self):
        with tempfile.TemporaryDirectory() as d:
            body, page = pathlib.Path(d) / "body.html", pathlib.Path(d) / "page.html"
            body.write_text(TWO_CHARTS)
            self.assertEqual(assemble(str(body), str(page)).returncode, 0)
            text = page.read_text()
            first = parts((REFS / "chart.html").read_text())[0]
            for block in first:
                self.assertEqual(text.count(block.strip()), 1, block[:60])
            self.assertIn("<title>도시별 요청</title>", text)
            r = subprocess.run([sys.executable, str(CHECK), str(page)], capture_output=True, text=True)
            self.assertEqual(r.stdout.splitlines()[-1], "pass", r.stdout)


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

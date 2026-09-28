"""The page skin at phone width: one gothic face for every text role, and a wide table held in its scroll box.

Run: uvx --with playwright pytest mumu-paperwork/tests -q
"""
import pathlib
import re
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIN = ROOT / "skills" / "rendering" / "references" / "page.html"
CHROME = pathlib.Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
# the textbook pair: Myeongjo for the chapter title and reading text, Gothic for headings, captions and controls
SERIF, FACE = "Nanum Myeongjo", "Nanum Gothic"
ROLES = ("h1", "h2", "h3", "main > p", "button", "figcaption", "caption", "th", "td", "footer")
COLUMNS = ("작업", "요청(건)", "오류(건)", "평균(ms)", "최대(ms)")
ROWS = [("수집기", "1,240,000", "12,480", "1,204", "98,310"),
        ("정리기", "87,000", "3,905", "15,870", "240,112"),
        ("보고서", "3,905,210", "210", "402", "12,004")]
MAIN = """<main>
  <h1>작업 목록</h1>
  <p class="read">정리기가 멈춰 있어요.</p>
  <h2 id="s1">작업별 상태</h2>
  <h3 id="s1-a">이번 주</h3>
  <p>세 <dfn>작업</dfn>을 비교해요.</p>
  <div class="scroll" role="region" aria-labelledby="t-jobs" tabindex="0"><table>
    <caption id="t-jobs">작업 세 개</caption>
    <thead><tr>%s</tr></thead>
    <tbody>%s</tbody>
  </table></div>
  <figure><figcaption>그림 설명이에요.</figcaption></figure>
  <button type="button">다음</button>
  <footer>출처 <code>abc1234</code></footer>
</main>""" % (
    "".join(f'<th scope="col">{c}</th>' for c in COLUMNS),
    "".join(f'<tr><th scope="row">{r[0]}</th>' + "".join(f'<td class="num">{v}</td>' for v in r[1:]) + "</tr>"
            for r in ROWS))
PROBE = """() => {
  const box = document.querySelector('.scroll'), first = box.querySelector('tbody th'), e = document.documentElement;
  const css = (el) => getComputedStyle(el);
  const out = { scroll: e.scrollWidth, inner: innerWidth, boxScroll: box.scrollWidth, boxClient: box.clientWidth,
    name: document.getElementById(box.getAttribute('aria-labelledby'))?.textContent,
    caption: css(box.querySelector('caption')).textAlign, num: css(box.querySelector('td.num')).textAlign,
    dfn: css(document.querySelector('dfn')).fontStyle, faces: {} };
  for (const s of %s) out.faces[s] = css(document.querySelector(s)).fontFamily.split(',')[0].replace(/["']/g, '').trim();
  box.scrollLeft = box.scrollWidth;
  out.scrolled = box.scrollLeft;
  out.held = Math.round(first.getBoundingClientRect().left - box.getBoundingClientRect().left);
  out.opaque = css(first).backgroundColor;
  return out;
}""" % repr(list(ROLES)).replace("'", '"')


def page_html(skin):
    """The shell copied whole, its comment deleted and its main filled with a 5-column table."""
    html = re.sub(r"^<!--.*?-->\s*", "", skin, count=1, flags=re.S)
    return re.sub(r"<main>.*?</main>", lambda _: MAIN, html, count=1, flags=re.S).replace("{{title}}", "작업 목록")


def probe(skin):
    from playwright.sync_api import sync_playwright
    with tempfile.TemporaryDirectory() as d, sync_playwright() as p:
        f = pathlib.Path(d) / "page.html"
        f.write_text(page_html(skin))
        browser = p.chromium.launch(executable_path=str(CHROME))
        try:
            page = browser.new_page(viewport={"width": 360, "height": 800})
            page.goto(f.as_uri())
            out = page.evaluate(PROBE)
            page.keyboard.press("Tab")
            out["focused"] = page.evaluate("document.activeElement.className")
            out["outline"] = page.evaluate("getComputedStyle(document.activeElement).outlineStyle")
            return out
        finally:
            browser.close()


@unittest.skipUnless(CHROME.exists(), "no Chrome")
class PhoneTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = probe(SKIN.read_text())

    def test_page_does_not_scroll_sideways(self):
        self.assertLessEqual(self.r["scroll"], self.r["inner"], self.r)
        self.assertEqual(self.r["inner"], 360)

    def test_table_scrolls_in_its_named_box(self):
        self.assertGreater(self.r["boxScroll"], self.r["boxClient"], self.r)
        self.assertEqual(self.r["name"], "작업 세 개")
        self.assertEqual((self.r["focused"], self.r["outline"]), ("scroll", "solid"))

    def test_first_column_stays_in_view(self):
        self.assertEqual(self.r["scrolled"], self.r["boxScroll"] - self.r["boxClient"], self.r)
        self.assertGreater(self.r["scrolled"], 0)
        self.assertEqual(self.r["held"], 0, self.r)
        self.assertNotRegex(self.r["opaque"], r"rgba\(.*, 0\)|transparent")

    def test_caption_and_numbers_align(self):
        self.assertEqual((self.r["caption"], self.r["num"]), ("start", "end"))

    def test_each_text_role_takes_its_face(self):
        self.assertEqual(self.r["faces"], {s: SERIF if s in ("h1", "main > p", "td") else FACE for s in ROLES})

    def test_skin_loads_only_the_nanum_pair(self):
        skin = SKIN.read_text()
        self.assertEqual(re.findall(r"family=([^:&\"]+)", skin), ["Nanum+Gothic", "Nanum+Myeongjo"])
        self.assertNotRegex(skin, r"Playfair|Source Serif|Noto Serif")

    def test_defined_term_stands_upright(self):
        self.assertEqual(self.r["dfn"], "normal", "Hangul has no italic, so Chrome slants it")


ASSEMBLE = ROOT / "skills" / "rendering" / "scripts" / "assemble.py"
# where the focus is: its text, whether a closed drawer or a hidden element holds it
FOCUS = """() => { const a = document.activeElement;
  return [a.textContent.trim().slice(0, 20), !!a.closest('nav:not(.open)') && innerWidth < 1200, !a.checkVisibility({ visibilityProperty: true })]; }"""


def aids(width, steps, head=""):
    """Run `steps(page)` on tests/pages/widgets.html assembled, `width` px wide, `head` put before its first script."""
    import subprocess
    import sys
    from playwright.sync_api import sync_playwright
    with tempfile.TemporaryDirectory() as d, sync_playwright() as p:
        f = pathlib.Path(d) / "page.html"
        subprocess.run([sys.executable, str(ASSEMBLE), str(ROOT / "tests" / "pages" / "widgets.html"), str(f)], check=True,
                       capture_output=True)
        if head:
            f.write_text(f.read_text().replace("<main>", head + "<main>", 1))
        browser = p.chromium.launch(executable_path=str(CHROME))
        try:
            page = browser.new_page(viewport={"width": width, "height": 800})
            page.goto(f.as_uri() + "#c1")
            page.wait_for_timeout(300)
            return steps(page)
        finally:
            browser.close()


@unittest.skipUnless(CHROME.exists(), "no Chrome")
class ReadingAids(unittest.TestCase):
    def test_tab_skips_closed_drawer_and_hidden_buttons(self):
        def steps(page):
            seen = []
            for _ in range(40):
                page.keyboard.press("Tab")
                seen.append(page.evaluate(FOCUS))
            return seen
        seen = aids(400, steps)
        self.assertEqual([s for s in seen if s[1] or s[2]], [], seen)
        self.assertIn("목차", [s[0] for s in seen])

    def test_drawer_opens_and_closes_by_button_escape_and_backdrop(self):
        def steps(page):
            js = "document.querySelector('main nav').checkVisibility({ visibilityProperty: true })"
            def shown(want):
                """Whether the drawer shows, once it does as `want` or 5 s pass, since a loaded machine slows its transition."""
                try:
                    page.wait_for_function(js if want else "!" + js, timeout=5000)
                except Exception:
                    pass
                return page.evaluate(js)
            out = [shown(False)]
            page.click(".dock .contents")
            out += [shown(True), page.evaluate("!!document.activeElement.closest('main nav')")]
            page.keyboard.press("Escape")
            out += [shown(False), page.evaluate("document.activeElement.className")]
            page.click(".dock .contents")
            shown(True)
            page.mouse.click(390, 400)
            return out + [shown(False)]
        self.assertEqual(aids(400, steps), [False, True, True, False, "contents", False])

    def test_open_drawer_keeps_tab_inside_it(self):
        def steps(page):
            page.click(".dock .contents")
            page.wait_for_function("document.querySelector('main nav').checkVisibility({ visibilityProperty: true })")
            seen = []
            for _ in range(30):
                page.keyboard.press("Tab")
                seen.append(page.evaluate("""() => { const a = document.activeElement;
                  return [a.textContent.trim().slice(0, 20), a === document.body || !!a.closest('main nav')]; }"""))
            return seen
        seen = aids(400, steps)
        self.assertEqual([s for s in seen if not s[1]], [], seen)
        self.assertTrue(any(s[0] for s in seen), seen)

    def test_back_waits_for_a_slow_chapter(self):
        # the chapter script's hashchange handler, the first one registered, runs 300 ms late
        slow = """<script>(() => { const add = window.addEventListener; let first = true;
          window.addEventListener = function (type, fn, ...rest) {
            if (type === 'hashchange' && first) { first = false; const f = fn; fn = (e) => setTimeout(() => f(e), 300); }
            return add.call(this, type, fn, ...rest); }; })();</script>"""
        def steps(page):
            page.evaluate("document.querySelector('#c1 + p a').scrollIntoView()")
            page.wait_for_timeout(200)
            y = page.evaluate("scrollY")
            page.click("#c1 + p a")
            page.wait_for_timeout(500)
            page.click(".dock .back")
            page.wait_for_timeout(800)
            return [y, page.evaluate("[scrollY, location.hash]")]
        y, back = aids(400, steps, head=slow)
        self.assertEqual(back[1], "#c1")
        self.assertLessEqual(abs(back[0] - y), 2, (y, back))

    def test_drawer_docks_open_from_1200px(self):
        r = aids(1300, lambda page: page.evaluate("""() => { const nav = document.querySelector('main nav');
          return [nav.checkVisibility({ visibilityProperty: true }), document.querySelector('.dock .contents').checkVisibility(),
                  nav.getBoundingClientRect().right <= document.querySelector('main').getBoundingClientRect().left]; }"""))
        self.assertEqual(r, [True, False, True])

    def test_heading_in_view_is_marked_in_the_shown_chapter(self):
        def steps(page):
            page.evaluate("document.getElementById('c1-b').scrollIntoView()")
            page.wait_for_timeout(200)
            return page.evaluate("[...document.querySelectorAll('main nav a.here')].map((a) => a.getAttribute('href'))")
        self.assertEqual(aids(400, steps), ["#c1-b"])

    def test_back_returns_to_the_spot_and_its_id_and_rebinds_no_key(self):
        def steps(page):
            page.evaluate("document.querySelector('#c1 + p a').scrollIntoView()")
            page.wait_for_timeout(200)
            y = page.evaluate("scrollY")
            page.click("#c1 + p a")
            page.wait_for_timeout(200)
            gone = page.evaluate("[location.hash, document.querySelector('.dock .back').checkVisibility()]")
            page.keyboard.press("Backspace")
            page.keyboard.press("ArrowLeft")
            page.wait_for_timeout(200)
            kept = page.evaluate("location.hash")
            page.click(".dock .back")
            page.wait_for_timeout(300)
            return [y, gone, kept, page.evaluate("[scrollY, location.hash, document.querySelector('.dock .back').hidden]")]
        y, gone, kept, back = aids(400, steps)
        self.assertEqual((gone, kept), (["#c3-lamp", True], "#c3-lamp"))
        self.assertEqual(back[1:], ["#c1", True])
        self.assertLessEqual(abs(back[0] - y), 2)


# each role's computed font size, in px, and whether it keeps the order h1 > h2 > h3 > body > table
SIZES = """() => { document.querySelector('main').append(document.createElement('h3'));
  const px = (s) => parseFloat(getComputedStyle(document.querySelector(s)).fontSize);
  return { h1: px('h1'), h2: px('h2'), h3: px('h3'), body: px('main > p:not(.read)'), table: px('td') }; }"""
# per table cell, [whether it is a number cell, its line count, the fewest characters on one of its lines]
CELLS = """() => [...document.querySelectorAll('#t-jobs ~ tbody :is(th, td), #t-jobs ~ thead th')].map((c) => {
  const lines = new Map(), walk = document.createTreeWalker(c, NodeFilter.SHOW_TEXT);
  for (let n; (n = walk.nextNode());) for (let i = 0; i < n.data.length; i++) {
    if (!n.data[i].trim()) continue;
    const r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + 1);
    const top = Math.round(r.getBoundingClientRect().top);
    lines.set(top, (lines.get(top) || 0) + 1);
  }
  return [c.classList.contains('num'), c.textContent.trim(), lines.size, Math.min(...lines.values())]; })"""
WIDE = """() => [document.documentElement.scrollWidth, innerWidth]"""
# page width, then the marked line's box width against its pre's content box width
QUOTE = """() => { const pre = document.querySelector('figure.code pre'), s = getComputedStyle(pre);
  return [document.documentElement.scrollWidth, innerWidth, pre.querySelector('mark').getBoundingClientRect().width,
    pre.clientWidth - parseFloat(s.paddingLeft) - parseFloat(s.paddingRight)]; }"""


def overflow_page(width, steps):
    """Run `steps(page)` on tests/pages/overflow.html assembled, `width` px wide, each details open."""
    import subprocess
    import sys
    from playwright.sync_api import sync_playwright
    with tempfile.TemporaryDirectory() as d, sync_playwright() as p:
        f = pathlib.Path(d) / "page.html"
        subprocess.run([sys.executable, str(ASSEMBLE), str(ROOT / "tests" / "pages" / "overflow.html"), str(f)], check=True,
                       capture_output=True)
        browser = p.chromium.launch(executable_path=str(CHROME))
        try:
            page = browser.new_page(viewport={"width": width, "height": 800})
            page.goto(f.as_uri())
            page.wait_for_timeout(300)
            page.evaluate("document.querySelectorAll('details').forEach((d) => { d.open = true; })")
            return steps(page)
        finally:
            browser.close()


@unittest.skipUnless(CHROME.exists(), "no Chrome")
class PhoneType(unittest.TestCase):
    def test_body_is_10pt_and_sizes_keep_their_order(self):
        s = overflow_page(360, lambda page: page.evaluate(SIZES))
        self.assertAlmostEqual(s["body"], 40 / 3, places=1, msg="10pt, 2pt under 16px = 12pt")
        self.assertGreater(s["h1"], s["h2"], s)
        self.assertGreater(s["h2"], s["h3"], s)
        self.assertGreater(s["h3"], s["body"], s)
        self.assertGreater(s["body"], s["table"], s)

    def test_table_cells_read_at_320px(self):
        cells = overflow_page(320, lambda page: page.evaluate(CELLS))
        self.assertTrue(any(n for n, *_ in cells) and any(not n for n, *_ in cells), cells)
        self.assertEqual([c for c in cells if c[0] and c[2] > 1], [], "a number wraps")
        self.assertEqual([c for c in cells if not c[0] and c[2] > 1 and c[3] < 4], [], "a line under 4 characters")

    def test_page_keeps_its_width_with_over_long_content(self):
        def steps(page):
            page.click("a[href='#s-tree']:not(nav a)")
            page.wait_for_timeout(300)
            return page.evaluate(WIDE) + [page.evaluate("document.querySelector('.dock .back').checkVisibility()")]
        for width in (320, 360):
            with self.subTest(width):
                scroll, inner, back = overflow_page(width, steps)
                self.assertTrue(back)
                self.assertLessEqual(scroll, inner)

    def test_code_quote_fits_and_marks_whole_line(self):
        scroll, inner, mark, content = overflow_page(320, lambda page: page.evaluate(QUOTE))
        self.assertLessEqual(scroll, inner, "a long path caption widens the page")
        self.assertAlmostEqual(mark, content, delta=1, msg="the mark fills the pre's line")


if __name__ == "__main__":
    unittest.main()

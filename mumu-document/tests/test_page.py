"""The page skin at phone width: one gothic face for every text role, and a wide table held in its scroll box.

Run: uvx --with playwright pytest mumu-document/tests -q
"""
import pathlib
import re
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIN = ROOT / "skills" / "writing-documents" / "references" / "page.html"
CHROME = pathlib.Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
FACE = "Nanum Gothic"
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

    def test_every_text_role_is_nanum_gothic(self):
        self.assertEqual(self.r["faces"], {s: FACE for s in ROLES})

    def test_skin_loads_only_nanum_gothic(self):
        skin = SKIN.read_text()
        self.assertEqual(re.findall(r"family=([^:&\"]+)", skin), ["Nanum+Gothic"])
        self.assertNotRegex(skin, r"Playfair|Source Serif|Noto Serif|AppleMyungjo")

    def test_defined_term_stands_upright(self):
        self.assertEqual(self.r["dfn"], "normal", "Hangul has no italic, so Chrome slants it")


if __name__ == "__main__":
    unittest.main()

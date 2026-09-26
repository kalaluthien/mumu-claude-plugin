"""diagram.html's script and played styles, driven in Chrome: gaps, focus highlight, legend, keyboard, touch, fallbacks.

Run: uvx --with playwright pytest mumu-document/tests -q
"""
import re
import unittest

from test_scripts import CHROME, REFS, in_state, parts

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

# (kind, edits to its template, the node to focus, nodes it reaches, a node it does not reach)
TREE = ".stage > ul > li > details > ul > li"
FOCUS = [
    ("file-tree", [], f"{TREE}:first-child summary", [".stage > ul > li > details > summary"], f"{TREE}[data-change='modify'] .name"),
    ("system-context", [], "rect.box.k1", ["rect.box.main", ".part:nth-of-type(1) .edge"], "rect.box.k2"),
    # the reply joins A and C; without it, C is not reached from A
    ("use-case", [(re.compile(r'\s*<g class="part" tabindex="0" data-step="3">.*?</g>', re.S), "")],
     "rect.box:nth-of-type(1)", ["rect.box:nth-of-type(2)", ".part[data-step='1'] .edge"], "rect.box:nth-of-type(3)"),
]
OPACITY = "(el) => { let o = 1; for (; el; el = el.parentElement) o *= +getComputedStyle(el).opacity; return o; }"
# every node and line that is not full, shown and laid out, all folders open and revealed
FADED = """(root) => { root.querySelectorAll('details').forEach((d) => { d.open = true; });
  document.getAnimations().forEach((a) => a.finish());  // the skin's reveal of an opened folder
  return [...root.querySelectorAll('.box, .part > *, svg > text, .stage li, .stage li > *, .stage details > *')].filter((el) => {
    let o = 1; for (let e = el; e; e = e.parentElement) o *= +getComputedStyle(e).opacity;
    return o < 1 || getComputedStyle(el).visibility !== 'visible' || !el.getClientRects().length; }).map((el) => el.outerHTML.slice(0, 60)); }"""


def page(kind, edits=()):
    blocks, body = parts((REFS / "diagram.html").read_text())
    section = next(s for s in re.split(r"\n(?=<section)", body.strip()) if f'data-diagram="{kind}"' in s)
    for old, new in edits:
        section, n = (old.subn(new, section) if hasattr(old, "subn") else (section.replace(old, new), section.count(old)))
        assert n, old
    blocks += parts((REFS / "page.html").read_text())[0]
    return ('<!doctype html><html lang="ko"><meta charset="utf-8"><title>그림</title>'
            + "".join(b for b in blocks if b.startswith("<style")) + "<main>"
            + in_state(section.replace("{{id}}", "d"), "default") + "</main>"
            + "".join(b for b in blocks if b.startswith("<script")) + "</html>")


@unittest.skipUnless(CHROME.exists() and sync_playwright, "no Chrome or playwright")
class Diagram(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(channel="chrome")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def open(self, html, **context):
        ctx = self.browser.new_context(viewport={"width": 400, "height": 900}, **context)
        self.addCleanup(ctx.close)
        p = ctx.new_page()
        p.route(re.compile(r"^https?://"), lambda r: r.abort())
        p.set_content(html)
        self.base = p.locator("[data-widget]").evaluate(FADED)  # the played steps still pending
        return p

    def opacity(self, p, selector):
        return p.locator(selector).first.evaluate(OPACITY)

    def assert_focused(self, p, reached, far, why, before=1):
        for sel in reached:
            self.assertEqual(self.opacity(p, sel), 1, f"{why}: {sel} dimmed")
        self.assertLess(self.opacity(p, far), before, f"{why}: {far} not dimmed")

    def assert_restored(self, p, why, want=None):
        self.assertEqual(p.locator("[data-widget]").evaluate(FADED), self.base if want is None else want, why)

    def test_pending_add_takes_no_space(self):
        p = self.open(page("file-tree"))
        p.evaluate("document.querySelectorAll('details').forEach((d) => { d.open = true; })")
        height = lambda: p.locator(".stage").evaluate("(s) => s.getBoundingClientRect().height")
        empty = ("(s) => [...s.querySelectorAll('li')].filter((li) => li.getBoundingClientRect().height > 0"
                 " && getComputedStyle(li).opacity === '0').length")
        first = height()
        self.assertEqual(p.locator(".stage").evaluate(empty), 0, "a row box sits empty at step 1")
        next_ = p.locator(".controls button").nth(1)
        while next_.is_enabled():
            next_.click()
        self.assertLess(first, height(), "the tree is no shorter at step 1 than at its last step")
        self.assertEqual(p.locator("li[data-change='add']").evaluate(OPACITY), 1)

    def test_focus_highlights_connections(self):
        for kind, edits, node, reached, far in FOCUS:
            with self.subTest(kind):
                p = self.open(page(kind, edits))
                before = self.opacity(p, far)  # a played node still pending is already faded
                p.hover(node, position={"x": 4, "y": 4})
                self.assert_focused(p, [node] + reached, far, "hover", before)
                p.mouse.move(399, 899)
                self.assert_restored(p, "hover off")

    def test_legend_filters_kind(self):
        p = self.open(page("system-context"))
        buttons = p.locator(".legend button")
        self.assertEqual(buttons.count(), 2)
        self.assertEqual(buttons.first.get_attribute("aria-pressed"), "true")
        buttons.first.click()
        self.assertEqual(buttons.first.get_attribute("aria-pressed"), "false")
        self.assertLess(self.opacity(p, "rect.box.k1"), 1)
        self.assertLess(self.opacity(p, ".part:nth-of-type(1) .edge"), 1)
        for sel in ("rect.box.k2", "rect.box.main", ".part:nth-of-type(2) .edge"):
            self.assertEqual(self.opacity(p, sel), 1, sel)
        buttons.first.click()
        self.assert_restored(p, "legend back on")

    def test_keyboard(self):
        p = self.open(page("system-context"))
        for _ in range(12):
            p.keyboard.press("Tab")
            if p.evaluate("document.activeElement.matches('rect.box.k1')"):
                break
        else:
            self.fail("Tab never reaches a node")
        self.assert_focused(p, ["rect.box.main"], "rect.box.k2", "Tab")
        p.keyboard.press("Escape")
        self.assert_restored(p, "Escape")
        p.keyboard.press("Enter")
        self.assert_focused(p, ["rect.box.main"], "rect.box.k2", "Enter")
        p.keyboard.press("Escape")
        p.keyboard.press(" ")
        self.assert_focused(p, ["rect.box.main"], "rect.box.k2", "Space")
        p.keyboard.press("Escape")
        self.assert_restored(p, "Escape after Space")
        p.locator(".legend button").first.focus()
        p.keyboard.press(" ")
        self.assertEqual(p.locator(".legend button").first.get_attribute("aria-pressed"), "false")

    def test_tap(self):
        p = self.open(page("system-context"), has_touch=True, is_mobile=True)
        p.tap("rect.box.k1", position={"x": 4, "y": 4})
        self.assert_focused(p, ["rect.box.main"], "rect.box.k2", "tap")
        p.tap("rect.box.k1", position={"x": 4, "y": 4})
        self.assert_restored(p, "second tap")
        p.tap(".legend button >> nth=1")
        self.assertEqual(p.locator(".legend button").nth(1).get_attribute("aria-pressed"), "false")
        self.assertLess(self.opacity(p, "rect.box.k2"), 1)

    def test_nothing_fades_without_script_motion_or_screen(self):
        for kind, edits, node, _, _ in FOCUS:
            with self.subTest(kind, mode="no script"):
                self.assert_restored(self.open(page(kind, edits), java_script_enabled=False), "no script", [])
            with self.subTest(kind, mode="reduced motion"):
                self.assert_restored(self.open(page(kind, edits), reduced_motion="reduce"), "reduced motion", [])
            with self.subTest(kind, mode="print"):
                p = self.open(page(kind, edits))
                p.click(node, position={"x": 4, "y": 4})
                if p.locator(".legend button").count():
                    p.locator(".legend button").first.click()
                p.emulate_media(media="print")
                self.assert_restored(p, "print", [])
                self.assertEqual(p.locator(".legend").evaluate_all("(l) => l.filter((e) => e.getClientRects().length).length"), 0)


if __name__ == "__main__":
    unittest.main()

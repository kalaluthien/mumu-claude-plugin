"""chart.html's script, driven in Chrome: it draws its charts wherever it sits in the page.

Run: uvx --with playwright pytest mumu-document/tests -q
"""
import re
import sys
import unittest

from test_scripts import CHROME, FIXTURES, REFS, in_state, parts

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


def page(script_first):
    """The chart fixtures in the skin, chart.html's script before them or after."""
    blocks = parts((REFS / "chart.html").read_text())[0] + parts((REFS / "page.html").read_text())[0]
    styles = "".join(b for b in blocks if b.startswith("<style"))
    scripts = "".join(b for b in blocks if b.startswith("<script"))
    main = "<main>" + in_state(FIXTURES["chart"], "default") + "</main>"
    return ('<!doctype html><html lang="ko"><meta charset="utf-8"><title>차트</title>' + styles
            + (scripts + main if script_first else main + scripts) + "</html>")


@unittest.skipUnless(CHROME.exists() and sync_playwright, "no Chrome or playwright")
class Chart(unittest.TestCase):
    def test_script_draws_wherever_it_sits(self):
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome")
            try:
                for first in (False, True):
                    with self.subTest(script_first=first):
                        p = browser.new_page(viewport={"width": 400, "height": 900})
                        p.route(re.compile(r"^https?://"), lambda r: r.abort())
                        p.set_content(page(first))
                        plots = p.locator(".plot").evaluate_all("(ps) => ps.map((p) => p.querySelectorAll('svg .mark').length)")
                        self.assertEqual(len(plots), FIXTURES["chart"].count('class="plot"'))
                        self.assertNotIn(0, plots, "a .plot left undrawn")
            finally:
                browser.close()

    def test_assembled_slide_starts_at_its_first_table(self):
        sys.path.insert(0, str(REFS.parent / "scripts"))
        from assemble import assemble
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome")
            try:
                p = browser.new_page(viewport={"width": 400, "height": 900})
                p.route(re.compile(r"^https?://"), lambda r: r.abort())
                p.set_content(assemble("<h1>차트</h1>" + FIXTURES["chart"]))
                at = p.locator('[data-widget="chart"][data-slide]').evaluate_all("(fs) => fs.map((f) => f.dataset.at)")
                self.assertTrue(at)
                self.assertEqual(set(at), {"0"}, "a played chart opens at its first step")
            finally:
                browser.close()

    def open(self, pw):
        browser = pw.chromium.launch(channel="chrome")
        p = browser.new_page(viewport={"width": 400, "height": 900})
        p.route(re.compile(r"^https?://"), lambda r: r.abort())
        p.set_content(page(False))
        return browser, p

    def tip(self, p, fig):
        return fig.locator(".tip").evaluate("(t) => t.hidden ? null : t.textContent")

    def test_keyboard_reads_each_value(self):
        with sync_playwright() as pw:
            browser, p = self.open(pw)
            try:
                fig = p.locator('[data-widget="chart"]').first
                stops = fig.locator(".mark").evaluate_all("(ms) => ms.filter((m) => m.tabIndex === 0).length")
                self.assertEqual(stops, 1, "one Tab stop per chart")
                first = fig.locator(".mark").first
                first.focus()
                self.assertEqual(self.tip(p, fig), first.get_attribute("aria-label"))
                p.keyboard.press("ArrowDown")
                second = fig.locator(".mark").nth(1)
                self.assertTrue(second.evaluate("(m) => m === document.activeElement"), "an arrow moves to the next mark")
                self.assertEqual(self.tip(p, fig), second.get_attribute("aria-label"))
                p.keyboard.press("Escape")
                self.assertIsNone(self.tip(p, fig))
            finally:
                browser.close()

    def test_pointer_near_a_small_point_reads_it(self):
        with sync_playwright() as pw:
            browser, p = self.open(pw)
            try:
                fig = p.locator('[data-widget="chart"][data-chart="line"]').first
                dot = fig.locator("circle.mark").first
                box = dot.bounding_box()
                self.assertLess(box["width"], 24, "the point itself is smaller than a 24 px target")
                # 10 px off its centre, outside the point but inside a 24 px target
                x, y = box["x"] + box["width"] / 2 + 10, box["y"] + box["height"] / 2
                for touch in (False, True):
                    with self.subTest(touch=touch):
                        p.mouse.move(0, 0)
                        if touch:
                            fig.locator(".plot").dispatch_event("pointerdown", {"pointerType": "touch", "clientX": x, "clientY": y, "bubbles": True})
                        else:
                            p.mouse.move(x, y)
                        self.assertEqual(self.tip(p, fig), dot.get_attribute("aria-label"))
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()

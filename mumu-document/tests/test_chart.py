"""chart.html's script, driven in Chrome: it draws its charts wherever it sits in the page.

Run: uvx --with playwright pytest mumu-document/tests -q
"""
import re
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


if __name__ == "__main__":
    unittest.main()

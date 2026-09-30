"""The ui-diff widget played by the slide: its steps, row states, status lines and code chips, and check.py on its page.

Run: uvx --with playwright pytest paperwork/tests -q
"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "rendering" / "scripts"
BODY = ROOT / "tests" / "pages" / "ui-diff.html"
CHROME = pathlib.Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
# at step k: the caption, the step title, the count, each pane's shown status, the pane rows shown
READ = """() => {
  const root = document.querySelector('[data-widget="ui-diff"]'), shown = (e) => e.checkVisibility();
  return { caption: root.querySelector('.caption').textContent, title: root.querySelector('.step-title').textContent,
    count: root.querySelector('.count').textContent, slider: root.querySelector('.controls input').value,
    status: [...root.querySelectorAll('.status')].map((s) => [...s.children].filter(shown).map((c) => c.textContent)),
    rows: [...root.querySelectorAll('.view > li')].filter(shown).map((r) => r.textContent) };
}"""
# each row state's look: its fill pattern and its border style
LOOKS = """() => Object.fromEntries([...document.querySelectorAll('.view > [data-now]')].map((r) => {
  const cs = getComputedStyle(r);
  return [r.dataset.now, [cs.backgroundImage, cs.borderTopStyle]];
}))"""


def assemble(d):
    page = pathlib.Path(d) / "ui-diff.html"
    r = subprocess.run([sys.executable, str(SCRIPTS / "assemble.py"), str(BODY), str(page)], capture_output=True, text=True)
    if r.returncode:
        raise AssertionError(f"the fixture does not assemble: {r.stderr.strip()}")
    return page


@unittest.skipUnless(CHROME.exists(), "no Chrome")
class Played(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.dir = tempfile.TemporaryDirectory()
        cls.page_path = assemble(cls.dir.name)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(executable_path=str(CHROME))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.dir.cleanup()

    def open(self, width=640, scheme="light"):
        page = self.browser.new_page(viewport={"width": width, "height": 900}, color_scheme=scheme)
        self.errors = []
        page.on("pageerror", lambda e: self.errors.append(str(e)))
        page.route("http*://**", lambda r: r.abort())
        page.goto(self.page_path.as_uri())
        self.addCleanup(page.close)
        return page

    def step(self, page, k):
        page.evaluate("(k) => { const s = document.querySelector('[data-slide] .controls input');"
                      " s.value = k; s.dispatchEvent(new Event('input', { bubbles: true })); }", k)
        return page.evaluate(READ)

    def test_next_back_and_slider_move_the_step(self):
        page = self.open()
        first = page.evaluate(READ)
        self.assertEqual((first["caption"][:2], first["title"], first["count"]), ("1.", "단계 1 · 처음 추정", "1 / 4"))
        page.get_by_role("button", name="다음").click()
        self.assertEqual(page.evaluate(READ)["title"], "단계 2 · 높이 계산")
        self.assertEqual(page.evaluate(READ)["slider"], "2")
        page.get_by_role("button", name="뒤로").click()
        self.assertEqual(page.evaluate(READ), first)
        slid = self.step(page, 4)
        self.assertEqual((slid["caption"][:2], slid["title"], slid["count"]), ("4.", "단계 4 · 보여 주기", "4 / 4"))
        self.assertTrue(page.get_by_role("button", name="다음").is_disabled())
        self.assertEqual(self.errors, [])

    def test_a_stepped_part_shows_from_its_step(self):
        page = self.open()
        for k in (1, 2, 3, 4):
            with self.subTest(step=k):
                self.assertEqual("footer 32" in self.step(page, k)["rows"], k >= 4)
        self.assertEqual(self.errors, [])

    def test_row_states_differ_by_pattern_or_border(self):
        page = self.open()
        looks = {}
        for k in (1, 3, 4):
            self.step(page, k)
            looks.update(page.evaluate(LOOKS))
        self.assertEqual(set(looks), {"estimated", "measured", "revealed"})
        for a, b in (("estimated", "measured"), ("measured", "revealed"), ("estimated", "revealed")):
            with self.subTest(pair=(a, b)):
                self.assertNotEqual(looks[a], looks[b])
        self.assertEqual(looks["estimated"][1], "dashed")
        self.assertIn("gradient", looks["measured"][0])
        self.assertNotIn("gradient", looks["revealed"][0])

    def test_status_lines_follow_the_step(self):
        page = self.open()
        got = [self.step(page, k)["status"] for k in (1, 2, 3, 4)]
        self.assertEqual([s[0] for s in got], [["합계 1,788px · 11줄 · 숨김"], ["합계 1,788px · 11줄 · 숨김"],
                                               ["합계 1,788px · 11줄 · 측정 중"], ["합계 2,166px · 6줄 · 보임"]])
        self.assertEqual([s[1] for s in got], [["합계 1,788px · 11줄 · 숨김"], ["합계 2,166px · 6줄 · 숨김"],
                                               ["합계 2,166px · 6줄 · 숨김"], ["합계 2,166px · 6줄 · 보임"]])
        self.assertEqual(self.errors, [])

    def test_a_chip_marks_what_it_keys(self):
        page = self.open()
        keyed = "() => [...document.querySelectorAll('.keyed')].map((e) => e.id)"
        self.step(page, 2)
        page.get_by_role("button", name="line 1").hover()
        page.wait_for_timeout(50)
        self.assertEqual(page.evaluate(keyed), ["ud-l2"])
        self.assertNotEqual(page.eval_on_selector("#ud-l2", "(e) => getComputedStyle(e).backgroundColor"),
                            page.eval_on_selector("#ud-l3", "(e) => getComputedStyle(e).backgroundColor"))
        page.mouse.move(0, 0)
        page.wait_for_timeout(50)
        self.assertEqual(page.evaluate(keyed), [])
        self.step(page, 4)
        page.get_by_role("button", name="both").click()
        self.assertEqual(page.evaluate(keyed), ["ud-before", "ud-after"])
        self.assertEqual(page.eval_on_selector("#ud-before", "(e) => getComputedStyle(e).outlineStyle"), "solid")
        self.assertEqual(self.errors, [])

    def test_light_and_dark_hosts_draw_the_same_page_at_320(self):
        # the skin is always light, so check.py's run stands for a dark host too
        looks = {}
        for scheme in ("light", "dark"):
            page = self.open(320, scheme)
            self.step(page, 3)
            looks[scheme] = page.evaluate("() => [document.documentElement.scrollWidth <= innerWidth,"
                                          " getComputedStyle(document.body).backgroundColor,"
                                          " [...document.querySelectorAll('.view > li')].map((r) => getComputedStyle(r).backgroundColor)]")
        self.assertTrue(looks["light"][0], looks)
        self.assertEqual(looks["light"], looks["dark"])
        self.assertEqual(self.errors, [])


@unittest.skipUnless(CHROME.exists(), "no Chrome")
class Checked(unittest.TestCase):
    def test_check_passes_on_the_page(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(SCRIPTS / "check.py"), str(assemble(d))], capture_output=True, text=True,
                               timeout=600)
        self.assertEqual(r.stdout.strip().splitlines()[-1], "pass", r.stdout + r.stderr)

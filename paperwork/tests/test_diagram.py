"""diagram.html's script and played styles, driven in Chrome: gaps, focus highlight, legend, keyboard, touch, fallbacks.

Run: uvx --with playwright pytest paperwork/tests -q
"""
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

from test_scripts import ASSEMBLE, CHECK, CHROME, REFS, in_state, parts

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeout, sync_playwright
except ImportError:
    sync_playwright = None

# (kind, edits to its template, the node to focus, nodes it reaches, a node it does not reach)
TREE = ".stage > ul > li > details > ul > li"
FOCUS = [
    ("file-tree", [], f"{TREE}:first-child summary", [".stage > ul > li > details > summary"], f"{TREE}[data-change='modify'] .name"),
    ("system-context", [], "rect.box.k1", ["rect.box.main", ".part:nth-of-type(1) .edge"], "rect.box.k2"),
    # the reply joins A and C; without it, C is not reached from A
    ("use-case", [(re.compile(r'\s*<li style="--from: 3; --to: 1;">.*?</li>'), "")],
     ".flow > .box:nth-of-type(1)", [".flow > .box:nth-of-type(2)", ".flow li:nth-child(1)"], ".flow > .box:nth-of-type(3)"),
    ("network", [], "rect.box.k1", ["rect.box:nth-of-type(2)", "rect.box:nth-of-type(3)", ".part:nth-of-type(2) .edge"], "rect.box.k3"),
]
# the task graph, one application the task names: a task, what it blocks, its state as its kind
TASKS = [  # (label, kind, full name, [(target, edge class, link text)])
    ("페이지 위젯", "k3", "<code>#254</code> 카메라 페이지의 위젯을 지켜요.", [(2, "ok", "네트워크 그림을 풀어요"), (4, "ok", "검사 규칙을 풀어요"),
                                                          (9, "inferred", "마감 보고를 풀 수도 있어요")]),
    ("네트워크 그림", "k2", "<code>#295</code> 그림 위젯에 네트워크 종류를 더해요.", [(5, "warn", "스킬 표 갱신을 막아요"), (6, "", "평가 실행을 막아요")]),
    ("차트 점 지도", "k1", "<code>#284</code> 차트에 점 지도를 더해요.", [(6, "inferred", "평가 실행을 막을 수 있어요")]),
    ("검사 규칙", "k2", "<code>#271</code> 검사 규칙을 정리해요.", [(7, "", "규칙 정리를 막아요")]),
    ("스킬 표 갱신", "k1", "스킬 표에 새 위젯을 적어요.", [(8, "", "배포 안내를 막아요")]),
    ("평가 실행", "k1", "평가를 main과 비교해요.", [(8, "fail", "배포 안내를 막아요")]),
    ("규칙 정리", "k1", "겹치는 규칙을 합쳐요.", [(9, "", "마감 보고를 막아요")]),
    ("배포 안내", "k1", "리드에게 다시 읽기를 알려요.", [(9, "", "마감 보고를 막아요")]),
    ("마감 보고", "k1", "끝난 일을 보고해요.", []),
]


def network(tasks=TASKS):
    """The task graph as an author writes it: a dt per task, its dd the full name then a link per task it blocks."""
    rows = "".join(
        f'<dt id="n-t{i}" class="{kind}">{label}</dt>\n<dd>{name} ' + " ".join(
            f'<a{f" class={chr(34)}{c}{chr(34)}" if c else ""} href="#n-t{j}">{text}</a>' for j, c, text in links) + "</dd>\n"
        for i, (label, kind, name, links) in enumerate(tasks, 1))
    return ('<section aria-labelledby="n"><h2 id="n">작업이 서로 막는 관계</h2>\n'
            '<div data-widget="diagram" data-diagram="network" data-kinds="할 일|진행 중|끝남">\n'
            f'<figure class="stage scroll" tabindex="0" aria-labelledby="n"><dl>\n{rows}</dl>\n'
            '<figcaption class="muted">색은 작업의 상태, 점선은 짐작한 관계예요.</figcaption></figure></div></section>')


# the same graph with every label 8 syllables long, the most a label may have
LONG = [("가나다라마바사" + c,) + task[1:] for c, task in zip("아자차카타파하거너", TASKS)]


def layers(tasks=TASKS):
    """Each task's layer: the longest chain of blockers above it."""
    depth = {}
    def d(i):
        if i not in depth:
            depth[i] = max([d(j) + 1 for j, t in enumerate(tasks, 1) if any(k == i for k, _, _ in t[3])], default=0)
        return depth[i]
    return [d(i) for i in range(1, len(tasks) + 1)]
# a network's boxes, its label boxes, each line's first and last point, and the page's widths
SHAPES = """(svg) => { const n = (e, a) => +e.getAttribute(a), m = svg.getScreenCTM();
  const pt = (p) => ({ x: p.x, y: p.y });
  return { boxes: [...svg.querySelectorAll('rect.box')].map((b) => ({ x: n(b, 'x'), y: n(b, 'y'), w: n(b, 'width'), h: n(b, 'height') })),
    texts: [...svg.querySelectorAll(':scope > text')].map((t) => { const b = t.getBBox(); return { x: b.x, y: b.y, w: b.width, h: b.height }; }),
    ends: [...svg.querySelectorAll('.part .edge')].map((e) => [pt(e.getPointAtLength(0)), pt(e.getPointAtLength(e.getTotalLength()))]),
    scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth,
    figure: svg.getBoundingClientRect().width, stage: svg.parentElement.clientWidth }; }"""


def overlap(a, b):
    return min(a["x"] + a["w"], b["x"] + b["w"]) > max(a["x"], b["x"]) and min(a["y"] + a["h"], b["y"] + b["h"]) > max(a["y"], b["y"])


def inside(a, b):
    return b["x"] <= a["x"] and a["x"] + a["w"] <= b["x"] + b["w"] and b["y"] <= a["y"] and a["y"] + a["h"] <= b["y"] + b["h"]


def nearest(boxes, p):
    gap = lambda b: (max(b["x"] - p["x"], 0, p["x"] - b["x"] - b["w"]) ** 2 + max(b["y"] - p["y"], 0, p["y"] - b["y"] - b["h"]) ** 2)
    return min(range(len(boxes)), key=lambda i: gap(boxes[i]))


# a use case of 3 participants and 6 calls, from one of their lanes to another, labelled as an author labels them
CALLS = [(1, 2, "POST /jobs"), (2, 1, "id=7, queued 저장"), (3, 2, "리스 60초 요청"), (2, 3, "작업 7 넘김"),
         (3, 2, "done 기록"), (1, 2, "GET /jobs/7")]
# each text node's box that does not lie inside the widget's box, which a clipped or scrolled label leaves
CLIPPED = """(root) => { const w = root.getBoundingClientRect(), out = [], t = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n; (n = t.nextNode());) {
    if (!n.data.trim() || n.parentElement.closest('style, script, title, desc')) continue;
    const r = document.createRange(); r.selectNodeContents(n);  // an SVG text's range has no boxes: its element's box
    const boxes = n.parentElement instanceof SVGElement ? [n.parentElement.getBoundingClientRect()] : r.getClientRects();
    for (const b of boxes) if (b.width && (b.left < w.left - 1 || b.right > w.right + 1 || b.top < w.top - 1 || b.bottom > w.bottom + 1))
      out.push(n.data.trim().slice(0, 30)); }
  return [...new Set(out)]; }"""
OPACITY = "(el) => { let o = 1; for (; el; el = el.parentElement) o *= +getComputedStyle(el).opacity; return o; }"
# every node and line that is not full, shown and laid out, all folders open and revealed
FADED = """(root) => { root.querySelectorAll('details').forEach((d) => { d.open = true; });
  document.getAnimations().forEach((a) => a.finish());  // the skin's reveal of an opened folder
  return [...root.querySelectorAll('.box, .part > *, svg > text, .stage li, .stage li > *, .stage details > *')].filter((el) => {
    let o = 1; for (let e = el; e; e = e.parentElement) o *= +getComputedStyle(e).opacity;
    return o < 1 || getComputedStyle(el).visibility !== 'visible' || !el.getClientRects().length; }).map((el) => el.outerHTML.slice(0, 60)); }"""


def page(kind, edits=(), section=None, source=None):
    blocks, body = parts(source or (REFS / "diagram.html").read_text())
    section = section or next(s for s in re.split(r"\n(?=<section)", body.strip()) if f'data-diagram="{kind}"' in s)
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
        ctx = self.browser.new_context(**{"viewport": {"width": 400, "height": 900}, **context})
        self.addCleanup(ctx.close)
        p = ctx.new_page()
        p.route(re.compile(r"^https?://"), lambda r: r.abort())
        errors = []
        p.on("pageerror", lambda e: errors.append(str(e)))
        p.set_content(html)
        if context.get("java_script_enabled", True):
            try:  # a network is drawn once its fonts load; a copy without its script never draws it
                p.wait_for_function("!document.querySelector('[data-diagram=network] .stage > dl') || !!document.querySelector('.detail')",
                                    timeout=3000)
            except PlaywrightTimeout:
                pass
        self.assertEqual(errors, [], "the page threw")
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

    def test_use_case_is_one_still_figure(self):
        calls = "".join(f'<li style="--from: {i}; --to: {j};">{label}</li>' for i, j, label in CALLS)
        html = page("use-case", [(re.compile(r"<ol>.*?</ol>", re.S), f"<ol>{calls}</ol>")])
        p = self.open(html, viewport={"width": 320, "height": 800})
        root = p.locator("[data-widget]")
        self.assertEqual(root.locator("button, .steps").count(), 0, "a button or a step-card strip in the widget")
        text = root.text_content()
        self.assertEqual({label: text.count(label) for *_, label in CALLS}, {label: 1 for *_, label in CALLS}, "a label repeats")
        self.assertEqual(root.locator(".flow li").count(), len(CALLS))
        self.assertEqual(root.evaluate(CLIPPED), [], "a text box leaves the widget's box at 320 px")

    def test_every_focus_stop_has_a_role_and_a_name(self):
        stops = """(root) => [...root.querySelectorAll('[tabindex]:not([tabindex="-1"]), button, summary')].map((e) => [
          e.getAttribute('role') || e.localName, e.getAttribute('aria-label') || e.textContent.trim()])"""
        for kind in ("file-tree", "system-context", "use-case"):
            with self.subTest(kind):
                p = self.open(page(kind))
                got = p.locator("[data-widget]").evaluate(stops)
                self.assertTrue(got)
                self.assertTrue(any(role == "button" for role, _ in got), "no part is a button")
                for role, name in got:
                    self.assertIn(role, ("button", "summary", "figure", "region"), (role, name))
                    self.assertTrue(name, role)
                self.assertEqual(p.locator("[data-widget] svg[role='img']").count(), 0, "an img hides its buttons")
        p = self.open(page("system-context"))
        part = p.locator(".part").nth(1)
        self.assertEqual(part.get_attribute("aria-label"), "예시 예시 → 예시 예시")
        part.focus()
        p.keyboard.press("Enter")
        self.assertEqual(part.get_attribute("aria-pressed"), "true")

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

    def test_network_layout(self):
        cycle = [list(x) for x in TASKS]
        cycle[8] = cycle[8][:3] + [[(1, "", "페이지 위젯을 다시 막아요")]]  # the last task blocks the first: a cycle
        wide = self.open(page("network", section=network()), viewport={"width": 1200, "height": 800}).locator("svg").evaluate(SHAPES)
        rows = sorted(set(b["y"] for b in wide["boxes"]))
        self.assertEqual([rows.index(b["y"]) for b in wide["boxes"]], layers(), "not layered by longest path")
        for name, tasks in (("tasks", TASKS), ("long labels", LONG), ("cycle", cycle)):
            with self.subTest(name):
                shapes = [self.open(page("network", section=network(tasks)), viewport={"width": 320, "height": 800})
                          .locator("svg").evaluate(SHAPES) for _ in range(2)]
                self.assertEqual(shapes[0], shapes[1], "two loads draw different coordinates")
                g = shapes[0]
                self.assertEqual(g["scroll"], g["client"], "the page scrolls sideways")
                self.assertLessEqual(g["figure"], g["stage"], "the figure is wider than its column")
                boxes = g["boxes"]
                self.assertEqual(len(boxes), len(tasks))
                for (i, a), (j, b) in ((x, y) for x in enumerate(boxes) for y in enumerate(boxes) if x[0] < y[0]):
                    self.assertFalse(overlap(a, b), f"boxes {i + 1} and {j + 1} overlap")
                for i, (box, text) in enumerate(zip(boxes, g["texts"]), 1):
                    self.assertTrue(inside(text, box), f"label {i} spills out of its box: {text} {box}")
                links = [(i, j) for i, task in enumerate(tasks, 1) for j, _, _ in task[3]]
                self.assertEqual([(nearest(boxes, a) + 1, nearest(boxes, b) + 1) for a, b in g["ends"]], links)
                if name != "cycle":
                    for i, j in links:
                        self.assertLess(boxes[i - 1]["y"], boxes[j - 1]["y"], f"line {i}-{j} does not run down")

    def test_network_page_passes_check_up_to_nine_nodes(self):
        tenth = [("회고", "k1", "끝난 뒤 돌아봐요.", [])]
        for tasks, want in ((TASKS, "pass"), (TASKS + tenth, "FAIL")):
            with self.subTest(nodes=len(tasks)), tempfile.TemporaryDirectory() as d:
                body, out = pathlib.Path(d) / "body.html", pathlib.Path(d) / "page.html"
                body.write_text('<h1>작업 관계</h1>\n<p class="read">네트워크 그림이 두 작업을 막고 있어요.</p>\n' + network(tasks))
                r = subprocess.run([sys.executable, str(ASSEMBLE), str(body), str(out)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                r = subprocess.run([sys.executable, str(CHECK), str(out)], capture_output=True, text=True)
                self.assertEqual(r.stdout.splitlines()[-1], want, r.stdout)
                if want == "FAIL":
                    self.assertIn("network of 10 nodes over 9", r.stdout)

    def test_network_detail(self):
        p = self.open(page("network", section=network()))
        detail = p.locator("output.detail")
        self.assertEqual(detail.inner_text().strip(), "")
        self.assertEqual(detail.evaluate("(d) => d.getBoundingClientRect().height"), 0, "an empty panel takes room")
        p.hover("rect.box.k3", position={"x": 4, "y": 4})
        self.assertEqual(detail.get_attribute("aria-live"), "off", "a hover is announced")
        self.assertIn("페이지 위젯", detail.inner_text())
        self.assertIn("#254 카메라 페이지의 위젯을 지켜요.", detail.inner_text())
        p.mouse.move(399, 899)
        self.assertEqual(detail.inner_text().strip(), "", "hover off leaves the panel filled")
        p.click("rect.box.k3", position={"x": 4, "y": 4})
        p.mouse.move(399, 899)
        self.assertIn("#254", detail.inner_text(), "a click does not pin")
        self.assertEqual(detail.get_attribute("aria-live"), "polite", "a pin is not announced")
        p.keyboard.press("Escape")
        self.assertEqual(detail.inner_text().strip(), "", "Escape leaves the panel filled")
        p.mouse.move(399, 899)
        p.focus("rect.box:nth-of-type(2)")
        p.keyboard.press("Enter")
        self.assertIn("#295", detail.inner_text(), "focus and Enter do not fill the panel")
        p.mouse.move(399, 899)
        detail.get_by_text("평가 실행을 막아요").click()
        self.assertIn("평가를 main과 비교해요.", detail.inner_text(), "a panel link does not pin its target")
        self.assert_focused(p, ["rect.box:nth-of-type(6)", "rect.box:nth-of-type(2)", "rect.box:nth-of-type(8)"],
                            "rect.box:nth-of-type(1)", "panel link")
        p.mouse.move(399, 899)
        self.assertIn("평가를 main과 비교해요.", detail.inner_text(), "the pin does not stay")

    def test_network_focus_and_filter(self):
        p = self.open(page("network", section=network()))
        dimmed = "(r) => [...r.querySelectorAll('.dim')].length"
        before = p.locator("[data-widget]").evaluate(dimmed)
        p.click("rect.box:nth-of-type(2)", position={"x": 4, "y": 4})
        self.assert_focused(p, ["rect.box:nth-of-type(1)", "rect.box:nth-of-type(5)", "rect.box:nth-of-type(6)",
                                ".part:nth-of-type(4) .edge"], "rect.box:nth-of-type(3)", "click")
        p.keyboard.press("Escape")
        self.assertEqual(p.locator("[data-widget]").evaluate(dimmed), before, "Escape leaves nodes dimmed")
        p.locator(".legend button").nth(1).click()  # 진행 중: tasks 2 and 4
        gone = {2, 4}
        for i in range(1, len(TASKS) + 1):
            self.assertEqual(self.opacity(p, f"rect.box:nth-of-type({i})") < 1, i in gone, f"box {i}")
        links = [(i, j) for i, task in enumerate(TASKS, 1) for j, _, _ in task[3]]
        for n, (i, j) in enumerate(links, 1):
            self.assertEqual(self.opacity(p, f".part:nth-of-type({n}) .edge") < 1, bool({i, j} & gone), f"line {i}-{j}")

    def test_network_list_without_script_motion_or_screen(self):
        shown = "(dl) => dl.getBoundingClientRect().width > 100 && dl.checkVisibility()"
        for mode, context in (("no script", {"java_script_enabled": False}), ("reduced motion", {"reduced_motion": "reduce"}),
                              ("screen", {}), ("print", {})):
            with self.subTest(mode):
                p = self.open(page("network", section=network()), **context)
                if mode == "print":
                    p.click("rect.box.k3", position={"x": 4, "y": 4})
                    p.emulate_media(media="print")
                    self.assert_restored(p, "print", [])
                self.assertEqual(p.locator(".stage > dl").evaluate(shown), mode != "screen", mode)
                if mode != "print":  # a shown list's links take Tab, a hidden one's do not
                    self.assertEqual(p.locator(".stage > dl a").first.evaluate("(a) => a.tabIndex"), 0 if mode != "screen" else -1)

    def test_network_status_is_a_dash_not_a_colour(self):
        p = self.open(page("network", section=network()))
        style = lambda c: p.locator(f".part .edge{c}").first.evaluate(
            "(e) => [getComputedStyle(e).stroke, getComputedStyle(e).strokeDasharray]")
        plain, *rest = [style(c) for c in (":not(.ok, .warn, .fail, .inferred)", ".ok", ".warn", ".fail", ".inferred")]
        self.assertEqual({s for s, _ in [plain, *rest]}, {plain[0]}, "a status is a colour")
        self.assertEqual(len({d for _, d in [plain, *rest[1:]]}), 4, "two statuses share a dash")

    def test_must_fail_copies(self):
        source = (REFS / "diagram.html").read_text()
        # diagram.html before the network kind (#307), its blob at 3734462~1, which must fail; main has the kind since
        main = subprocess.run(["git", "show", "3f27c60140cb02ffd8971133c2696c054ad7f49d"],
                              capture_output=True, text=True, cwd=REFS).stdout
        copies = {"head": (source, None), "diagram.html before #307": (main, "drawn"),
                  "no panel update": (source.replace("        if (detail) note(on && source.get(on.el));\n", ""), "panel"),
                  "no width measurement": (source.replace("pen.measureText(t.textContent).width", "0"), "width"),
                  "no .detail exclusion": (source.replace("'.legend, .controls, .detail'", "'.legend, .controls'"), "pin")}
        for name, (copy, broken) in copies.items():
            with self.subTest(name):
                self.assertTrue(broken is None or copy != source, "the copy changes nothing")
                p = self.open(page("network", section=network(), source=copy))
                got = {"drawn": p.locator("svg rect.box").count() == len(TASKS)}
                if got["drawn"]:
                    g = p.locator("svg").evaluate(SHAPES)
                    got["width"] = all(inside(x, b) for x, b in zip(g["texts"], g["boxes"]))
                    p.hover("rect.box.k3", position={"x": 4, "y": 4})
                    got["panel"] = "#254" in p.locator(".detail").inner_text()
                    p.click("rect.box:nth-of-type(2)", position={"x": 4, "y": 4})
                    p.mouse.move(399, 899)
                    link = p.locator(".detail").get_by_text("평가 실행을 막아요")
                    if link.count():
                        link.click()
                    got["pin"] = "평가를 main과" in p.locator(".detail").inner_text()
                if broken:
                    self.assertFalse(got.get(broken, False), f"{name} passes {broken}")
                else:
                    self.assertEqual(set(got.values()), {True}, got)

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

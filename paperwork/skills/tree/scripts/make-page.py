#!/usr/bin/env python3
"""Build the answer page of a tree plan, and measure built pages in a browser.

usage: make-page.py PLAN.json OUT.html     one self-contained page; refused when the plan fails the checker
       make-page.py --check DIR            drive every DIR/X.json in headless Chromium and print one line per fact, ending in ok
       make-page.py --capture PAGE.html DIR  write first-screen.png, whole.png and phone.png of a built page into DIR
                                           (every call but the first needs playwright: uv run --with playwright==1.64.1 python3 make-page.py ...)
"""
import json
import pathlib
import re
import sys
import tempfile
import textwrap

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import tree_plan  # noqa: E402
from page import frame  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "page.html"
OPTION = '[data-option="{}:{}"]'
CLIPBOARD = ("clipboard-read", "clipboard-write")
CHANGE = 'change(() => { state.comments["1"] = ["x"]; })'
STATS = {"files": "#tree-files", "left": "#tree-left", "risks": "#tree-risks"}



def navigation(plan):
    """The left tree: each top-level Part with the Decisions under it; a goal stands in the Overview."""
    entries = [("overview", "Overview")]
    label = lambda part: textwrap.shorten(part["text"], 46, placeholder="…")
    for i, part in enumerate(plan["parts"], 1):
        if part.get("kind") == "goal" and not tree_plan.holds_decision(part):
            continue
        below = [(f"part-{part_id}", label(inside)) for part_id, inside in tree_plan.walk(part.get("parts", []), f"{i}.")
                 if tree_plan.is_decision(inside)]
        entries.append((f"part-{i}", label(part), below))
    return entries


def build(plan_path):
    plan = tree_plan.load_file(plan_path)
    errors = tree_plan.check(plan)
    if errors:
        raise tree_plan.PlanError(*errors[0])
    # "</" would end the script element early inside the embedded JSON.
    data = json.dumps(plan, ensure_ascii=False).replace("</", "<\\/")
    content = TEMPLATE.read_text(encoding="utf-8").replace("__STAMP__", tree_plan.stamp(plan)).replace("__PLAN__", data)
    return frame.build(plan["title"], content, navigation(plan))


class Skip(Exception):
    """The plan holds nothing this fact can measure."""


def needs(found):
    if not found:
        raise Skip
    return found


def press(page, part_id, position):
    page.evaluate("key => document.querySelector(key).click()", OPTION.format(part_id, position))


def write(page, key, text):
    page.locator(f'[data-key="{key}"]').click(force=True)
    page.locator(".editor-field").fill(text)
    page.keyboard.press("Enter")


def answer(page):
    return page.evaluate("answerText()")


def numbers(page):
    return {name: (int(re.search(r"\d+", page.inner_text(selector)).group()) if page.is_visible(selector) else None)
            for name, selector in STATS.items()}


def marked(page):
    return set(page.eval_on_selector_all(".frame-nav a[data-effect]", "links => links.map(link => link.hash.slice(6))"))


def reaches_top(page, part_id):
    return 0 <= page.evaluate("id => document.getElementById(id).getBoundingClientRect().top", f"part-{part_id}") <= frame.SECTION_TOP_LIMIT


def contrast(page, selector):
    return page.evaluate("""key => {
      const node = document.querySelector(key), ground = element => {
        const colour = getComputedStyle(element).backgroundColor;
        return colour === "rgba(0, 0, 0, 0)" ? ground(element.parentElement) : colour;
      };
      const light = colour => {
        const [r, g, b] = colour.match(/\\d+/g).map(n => n / 255).map(c => c <= .03928 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4);
        return .2126 * r + .7152 * g + .0722 * b;
      };
      const pair = [light(getComputedStyle(node).color), light(ground(node))].sort((a, b) => b - a);
      return (pair[0] + .05) / (pair[1] + .05);
    }""", selector)


class Facts:
    """One method per fact the browser measures; the method's name, with spaces for "_", is the fact."""

    def __init__(self, page, plan):
        self.page, self.plan = page, plan

    def left(self, answers=None):
        return tree_plan.waiting(tree_plan.evaluate(self.plan, answers))

    def answer(self):
        for part_id, entry in tree_plan.evaluate(self.plan).items():
            if not entry["cause"]:
                press(self.page, part_id, entry["blockers"].index(None) + 1)
        target = next((part_id for part_id, part in tree_plan.walk(self.plan["parts"]) if not tree_plan.holds_decision(part)), None)
        if target:
            write(self.page, f"Comment:{target}", "A comment")
            write(self.page, f"Edit:{target}", "New text")
            write(self.page, f"Strike:{target}", "Not needed")
            self.page.locator("#tree-undo").click()
            assert f"- {target} struck:" not in answer(self.page), "Undo left the strike in place"
            assert f"- {target} comment: A comment" in answer(self.page), "the comment is missing"
        self.page.locator("#frame-copy").click()
        self.page.wait_for_function("document.getElementById('frame-status').textContent === 'Copied'")
        text = self.page.evaluate("navigator.clipboard.readText()")
        tree_plan.check_head(self.plan, text)
        assert not tree_plan.check(tree_plan.apply_answer(self.plan, tree_plan.parse_answer(text))), "the next plan fails the checker"

    def blocked(self):
        base = tree_plan.evaluate(self.plan)
        turned = [(part_id, position, other_id, i) for part_id, position in tree_plan.presses(self.plan)
                  for other_id, entry in tree_plan.evaluate(self.plan, {part_id: position}).items() for i, blocker in enumerate(entry["blockers"], 1)
                  if blocker and not entry["cause"] and not tree_plan.settled(entry) and not base[other_id]["blockers"][i - 1]]
        part_id, position, other_id, blocked = needs(turned)[0]
        selector = OPTION.format(other_id, blocked)
        press(self.page, part_id, position)
        row, before = self.page.locator(f".option:has({selector})"), answer(self.page)
        assert row.is_visible() and "Blocked" in row.inner_text() and "⊘" in row.inner_text(), "the option lacks its icon and word"
        self.page.evaluate("key => document.querySelector(key).click()", selector)
        assert answer(self.page) == before, "a press changed the pick"
        cause = tree_plan.options(tree_plan.index(self.plan)[part_id])[position - 1]["text"]
        assert cause in row.inner_text(), f"the reason does not name {cause}"
        for theme in ("light", "dark"):
            self.page.evaluate("theme => { document.documentElement.dataset.theme = theme; }", theme)
            assert contrast(self.page, f".option:has({selector}) .blocked-reason") >= 4.5, f"the {theme} reason reads under 4.5:1"
        row.locator(".blocked-reason a").click()
        assert reaches_top(self.page, part_id), "the link does not bring the causing Decision to the top"

    def settled(self):
        found = [(part_id, position, other) for part_id, position in tree_plan.presses(self.plan)
                 for other, entry in tree_plan.evaluate(self.plan, {part_id: position}).items() if tree_plan.settled(entry)]
        part_id, position, folded = needs(found)[0]
        press(self.page, part_id, position)
        assert self.page.get_attribute(f'[id="part-{folded}"]', "data-state") == "settled", "the Decision is not marked settled"
        assert not self.page.is_visible(OPTION.format(folded, 1)), "the Decision does not fold"
        assert "1 auto-settled" in self.page.inner_text("#tree-folded"), "the overview shows no count"
        self.page.reload()
        assert self.page.eval_on_selector("#tree-queue li", "row => row.className") == "waiting", "an open Decision does not lead the overview"

    def effect(self):
        part_id, position = needs([item for item in tree_plan.presses(self.plan) if tree_plan.changes(self.plan, {}, *item)])[0]
        changed = tree_plan.changes(self.plan, {}, part_id, position)
        before, selector = self.page.inner_text(".tree-stats"), OPTION.format(part_id, position)
        self.page.locator(f".option:has({selector})").hover()
        assert marked(self.page) == changed, f"a hover marks {marked(self.page)}, not {changed}"
        assert self.page.inner_text(".tree-stats") != before, "a hover leaves the numbers as they were"
        self.page.mouse.move(0, 0)
        assert not marked(self.page) and self.page.inner_text(".tree-stats") == before, "the marks stay after the pointer leaves"
        self.page.locator(selector).focus()
        assert marked(self.page) == changed, f"a keyboard focus marks {marked(self.page)}, not {changed}"
        self.page.evaluate("document.activeElement.blur()")
        self.page.locator(selector).click()
        assert marked(self.page) == changed and self.page.inner_text(".tree-stats") != before, "a pick does not mark what it changed"

    def numbers(self):
        for part_id, position in tree_plan.presses(self.plan):
            reached = tree_plan.reachable(self.plan, part_id, position)
            if reached is None:
                continue
            answers = {**reached, part_id: position}
            self.page.evaluate("reset()")
            for other_id, chosen in sorted(answers.items(), key=lambda item: [int(n) for n in item[0].split(".")]):
                press(self.page, other_id, chosen)
            state = tree_plan.evaluate(self.plan, answers)
            want = {f"{other}:{i}" for other, entry in state.items() for i, blocker in enumerate(entry["blockers"], 1) if blocker}
            shown = set(self.page.eval_on_selector_all("[data-option][aria-disabled=true]", "rows => rows.map(row => row.dataset.option)"))
            assert shown == want, f"after {part_id} option {position} the page blocks {sorted(shown)}, the lib {sorted(want)}"
            assert numbers(self.page) == tree_plan.summary(self.plan, answers), f"after {part_id} option {position} the page shows {numbers(self.page)}"

    def estimate(self):
        files = needs(tree_plan.summary(self.plan)["files"])
        assert re.search(rf"~{files}\b.*estimate", self.page.inner_text("#tree-files")), f"the files read {self.page.inner_text('#tree-files')!r}"

    def exhibits(self):
        kinds = needs({part.get("kind") for _, part in tree_plan.walk(self.plan["parts"])} & {"mockup", "quote", "diff"})
        self.page.evaluate("document.querySelectorAll('.fold').forEach(press => press.click())")
        assert "mockup" not in kinds or self.page.eval_on_selector(".mock", "frame => parseFloat(getComputedStyle(frame).borderTopWidth)") > 0, "a mockup has no frame"
        assert "quote" not in kinds or self.page.inner_text(".quote cite").strip(), "a quote has no source"
        if "diff" in kinds:
            colours = [self.page.eval_on_selector(key, "line => getComputedStyle(line).backgroundColor") for key in (".diff-add", ".diff-remove")]
            assert colours[0] != colours[1], "added and removed lines share a colour"

    def next(self):
        needs(self.left())
        answers = {}
        while self.left(answers):
            target = self.left(answers)[0]
            self.page.locator("#tree-next").click()
            assert reaches_top(self.page, target), f"Next does not bring {target} to the top"
            answers[target] = tree_plan.evaluate(self.plan, answers)[target]["blockers"].index(None) + 1
            press(self.page, target, answers[target])
        assert self.page.locator("#tree-next").is_disabled(), "Next stays on with nothing open"

    def reload(self):
        part_id = needs(self.left())[0]
        press(self.page, part_id, 1)
        write(self.page, f"Comment:{part_id}", "Kept")
        before = answer(self.page)
        self.page.reload()
        assert answer(self.page) == before and self.page.get_attribute(OPTION.format(part_id, 1), "aria-pressed") == "true", "a reload loses the answers"

    def keys(self):
        left = needs(self.left()[1:] and self.left())
        self.page.keyboard.press("n")
        assert reaches_top(self.page, left[0]), "n does not reach the first open Decision"
        self.page.keyboard.press("1")
        assert f"- {left[0]} pick 1" in answer(self.page), "a number key does not pick"
        self.page.keyboard.press("j")
        assert self.page.evaluate("current") != left[0], "j does not move on"
        self.page.keyboard.press("k")
        assert self.page.evaluate("current") == left[0], "k does not move back"
        self.page.keyboard.press("u")
        assert answer(self.page) == tree_plan.answer_head(self.plan), "u does not undo"

    def pressed(self):
        part_id = needs(self.left())[0]
        assert answer(self.page) == tree_plan.answer_head(self.plan), "an untouched Decision wrote a line"
        press(self.page, part_id, 1)
        assert f"- {part_id} pick 1\n" in answer(self.page), "a press of option 1 wrote no line"

    def other(self):
        part_id = needs(self.left())[0]
        write(self.page, f"option:{part_id}:0", "My own way")
        assert f"- {part_id} other: My own way\n" in answer(self.page), "Other wrote no line"
        tree_plan.apply_answer(self.plan, tree_plan.parse_answer(answer(self.page)))

    def copied_only(self):
        for part_id in self.left()[:1]:
            press(self.page, part_id, 1)
        assert "# Answer:" not in self.page.inner_text("body") and not re.search(r"^- [\d.]+ pick", self.page.inner_text("body"), re.M), "the page shows the Answer"

    def at_once(self):
        selector = OPTION.format(needs(self.left())[-1], 1)
        self.page.locator(selector).scroll_into_view_if_needed()
        top = self.page.locator(selector).bounding_box()["y"]
        self.page.locator(selector).click()
        assert self.page.get_attribute(selector, "aria-pressed") == "true", "a pick does not apply at once"
        assert abs(self.page.locator(selector).bounding_box()["y"] - top) <= 1, "the pressed row moved"

    def delta(self):
        self.page.locator(f".option:has({OPTION.format(needs(self.left())[0], 1)})").hover()
        assert re.search(r"\d+ \([+-]\d+\)", self.page.inner_text("#tree-left")), f"a hover shows {self.page.inner_text('#tree-left')!r}"
        assert self.page.eval_on_selector(".tree-stats", "line => getComputedStyle(line).fontVariantNumeric") == "tabular-nums", "the digits are not tabular"

    def fold(self):
        for part_id, part in tree_plan.walk(self.plan["parts"]):
            if part.get("parts") and not tree_plan.is_decision(part):
                closed = self.page.locator(f'[id="part-{part_id}"] > .part-children').is_hidden()
                assert closed != tree_plan.holds_decision(part), f"part {part_id} is {'closed' if closed else 'open'}"


MEASURES = [name for name in vars(Facts) if not name.startswith("__") and name != "left"]


def check_dir(directory):
    from playwright.sync_api import sync_playwright
    failures, exercised = [], dict.fromkeys(MEASURES, 0)
    with sync_playwright() as driver, tempfile.TemporaryDirectory() as out:
        browser = driver.chromium.launch()
        for plan_path in sorted(pathlib.Path(directory).glob("*.json")):
            plan = tree_plan.load_file(plan_path)
            page_file = pathlib.Path(out) / (plan_path.stem + ".html")
            page_file.write_text(build(plan_path), encoding="utf-8")
            url = page_file.as_uri()
            for fact, why in frame.probe(browser, url, copied=tree_plan.answer_head(plan), change=CHANGE, state="answerText()").items():
                failures.append((fact, f"{plan_path.stem}: {why}"))
            for fact in MEASURES:
                with frame.opened(browser, url, frame.SCREEN_WIDTH, permissions=CLIPBOARD) as page:
                    dialogs = []
                    page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
                    try:
                        getattr(Facts(page, plan), fact)()
                        assert not dialogs, "a dialog opened"
                        exercised[fact] += 1
                    except Skip:
                        pass
                    except Exception as e:
                        failures.append((fact, f"{plan_path.stem}: {str(e).splitlines()[0]}"))
        browser.close()
    failed = {fact for fact, _ in failures}
    for fact, why in failures:
        print(f"failed {fact}: {why}", file=sys.stderr)
    for fact in (*frame.FACTS, *MEASURES):
        if fact not in failed and exercised.get(fact, 1):
            print(f"{fact.replace('_', ' ')} ok")
    print("Each line ending in ok names a fact the browser measured on the pages of this folder.")
    # A fact no plan exercised has measured nothing, so it fails instead of passing empty.
    return 1 if failed or not all(exercised.values()) else 0


def capture(page_html, out_dir):
    from playwright.sync_api import sync_playwright
    target = pathlib.Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    url = pathlib.Path(page_html).resolve().as_uri()
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        for name, width, whole in (("first-screen", frame.SCREEN_WIDTH, False), ("whole", frame.SCREEN_WIDTH, True), ("phone", frame.PHONE_WIDTH, True)):
            with frame.opened(browser, url, width) as page:
                page.screenshot(path=target / f"{name}.png", full_page=whole)
        browser.close()
    return 0


def main(args):
    if len(args) == 2 and args[0] == "--check":
        return check_dir(args[1])
    if len(args) == 3 and args[0] == "--capture":
        return capture(args[1], args[2])
    if len(args) != 2 or args[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        page = build(args[0])
    except tree_plan.PlanError as e:
        print(f"refused: {e}")
        return 1
    pathlib.Path(args[1]).write_text(page, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

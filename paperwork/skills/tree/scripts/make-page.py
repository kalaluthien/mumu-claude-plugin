#!/usr/bin/env python3
"""Build the answer page of a tree plan.

usage: make-page.py PLAN.json OUT.html     one self-contained page; refused when the plan fails the checker
       make-page.py --check DIR            drive every DIR/X.json in headless Chromium and print "ok N"
       make-page.py --layout DIR           measure every DIR/X.json's page as a tree and print "layout ok N"
       make-page.py --strategies DIR       drive every DIR/X.json's views (choices, stub, focus, fold, mockup, matters most)
                                           and print "strategies ok N"
       make-page.py --capture PAGE.html DIR  write the four review PNGs of a built page into DIR
       make-page.py --capture-all PAGE.html DIR  write every page of a built page, untouched, at 1200 px into DIR
                                           (the last three need playwright: uv run --with playwright==1.64.1 python3 make-page.py ...)
"""
import html
import json
import pathlib
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import tree_plan  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "page.html"


def build(plan_path):
    plan = tree_plan.load_file(plan_path)
    errs = tree_plan.check(plan)
    if errs:
        raise tree_plan.PlanError(*errs[0])
    # "</" would end the script element early inside the embedded JSON.
    data = json.dumps(plan, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8")
    return (page.replace("__TITLE__", html.escape(plan["title"])).replace("__STAMP__", tree_plan.stamp(plan))
            .replace("__PLAN__", data))


def strikeable(plan):
    """First non-Decision Part with no Decision inside it, so the pick still counts."""
    ids = tree_plan.index(plan)
    for pid, p in ids.items():
        inside = [q for i, q in ids.items() if i.startswith(pid + ".")]
        if not tree_plan.is_decision(p) and not any(tree_plan.is_decision(q) for q in inside):
            return pid
    return None


def later_ids(ids, decisions, answered):
    """The Parts the page must fade: after the first open Decision, outside its subtree."""
    open_ = next((d for d in decisions if d not in answered), None)
    if open_ is None:
        return set()
    order = list(ids)
    return {i for i in order[order.index(open_) + 1:] if not i.startswith(open_ + ".")}


def faded(page):
    return set(page.eval_on_selector_all(".part.later", "els => els.map(e => e.dataset.id)"))


def card_action(page, pid, label):
    page.hover(f'[data-id="{pid}"]')
    page.click(f'[data-id="{pid}"] > .acts button:text-is("{label}")')


def drive(browser_ctx, plan_path, out_dir):
    plan = tree_plan.load_file(plan_path)
    page_file = pathlib.Path(out_dir) / (pathlib.Path(plan_path).stem + ".html")
    page_file.write_text(build(plan_path), encoding="utf-8")
    page = browser_ctx.new_page()
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(page_file.as_uri())
    ids = tree_plan.index(plan)
    decisions = [i for i, p in ids.items() if tree_plan.is_decision(p)]
    if faded(page) != later_ids(ids, decisions, set()):
        raise AssertionError(f"faded on load {sorted(faded(page))}, expected {sorted(later_ids(ids, decisions, set()))}")
    if decisions:
        first = ids[decisions[0]]
        opts = tree_plan.options(first)
        k = 2 if len(opts) >= 2 else 1
        page.keyboard.press(str(k))
        q = opts[k - 1].get("then")
        if q:
            page.keyboard.press("2" if len(tree_plan.options(q)) >= 2 else "1")
    if decisions and faded(page) != later_ids(ids, decisions, {decisions[0]}):
        raise AssertionError(f"faded after the first pick {sorted(faded(page))}, expected {sorted(later_ids(ids, decisions, {decisions[0]}))}")
    target = strikeable(plan)
    # Outside the struck subtree, since a struck Part's descendants add no lines.
    commented = next((i for i in ids if not (target and (i == target or i.startswith(target + ".")))
                      and not tree_plan.is_decision(ids[i])), None) or decisions[0]
    page.click('[data-goto="plan"]')
    if target:
        card_action(page, target, "Strike")
        page.fill("section:not([hidden]) .ed-strike", "not needed")
        page.keyboard.press("Enter")
    card_action(page, commented, "Comment")
    page.fill("section:not([hidden]) .ed-comment", "checked by the page probe")
    page.keyboard.press("Enter")
    page.click("#copy")
    page.wait_for_function("document.getElementById('copy').textContent.startsWith('Copied')")
    try:
        text, how = page.evaluate("navigator.clipboard.readText()"), "clipboard"
        if not text:
            raise ValueError("empty")
    except Exception:
        text, how = page.input_value("#answer"), "textarea"
    page.close()
    if errors:
        raise AssertionError(f"console errors: {errors}")
    tree_plan.check_head(plan, text)
    entries = tree_plan.parse_answer(text)
    verbs = {e[2] for e in entries}
    need = {"comment"} | ({"struck"} if target else set())
    if not need <= verbs:
        raise AssertionError(f"answer lacks {sorted(need - verbs)}: {text!r}")
    if decisions and not ({"pick", "other"} & verbs):
        raise AssertionError(f"answer has no pick: {text!r}")
    nxt = tree_plan.apply_answer(plan, entries)
    errs = tree_plan.check(nxt)
    if errs:
        raise AssertionError(f"next plan refused: {errs[0]}")
    return how


ANSWER_BOX_JS = """() => { let m = 0;
  for (const e of document.querySelectorAll('body *')) {
    const own = typeof e.value === 'string' ? e.value
      : [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('');
    if (own.includes('# Answer:') && e.getClientRects().length) m = Math.max(m, e.getBoundingClientRect().height);
  } return Math.round(m); }"""
STRAY_BUTTONS_JS = """() => [...document.querySelectorAll('button')]
  .filter(b => b.getClientRects().length && !b.closest('.node, header, #bar')).length"""
OPTIONS_LEFT_JS = """() => { const s = document.querySelector('section:not([hidden])');
  const q = s.querySelector('.qcard').getBoundingClientRect().right;
  return [...s.querySelectorAll('.onode')].filter(o => o.getBoundingClientRect().left < q).length; }"""


def page_ids(page):
    return page.eval_on_selector_all("#pager [data-goto]", "els => els.map(e => e.dataset.goto)")


def measure(browser, plan_path, out_dir):
    """The facts that make the page a tree; returns the first that fails, or None."""
    page_file = pathlib.Path(out_dir) / (pathlib.Path(plan_path).stem + ".html")
    page_file.write_text(build(plan_path), encoding="utf-8")
    sent = []
    wide = browser.new_page(viewport={"width": 1200, "height": 900})
    wide.on("request", lambda r: sent.append(r.url) if not r.url.startswith(("file:", "data:")) else None)
    wide.goto(page_file.as_uri())
    box = wide.evaluate(ANSWER_BOX_JS)
    if box:
        return f"the Answer text shows in a box {box} px tall"
    for pid in page_ids(wide):
        wide.click(f'[data-goto="{pid}"]')
        stray = wide.evaluate(STRAY_BUTTONS_JS)
        if stray:
            return f"page {pid}: {stray} buttons outside a node card, the header and the bottom bar"
        if pid != "plan" and wide.evaluate(OPTIONS_LEFT_JS):
            return f"page {pid}: an Option card starts left of the question card's right edge at 1200 px"
    wide.click('[data-goto="plan"]')
    card_action(wide, "1", "Edit")
    wide.fill("section:not([hidden]) .ed-edit", "edited by the layout probe")
    wide.keyboard.press("Enter")
    if "- 1 edited: edited by the layout probe" not in wide.input_value("#answer"):
        return "an Edit of Part 1 is missing from the Answer"
    wide.click("#undo")
    if "edited:" in wide.input_value("#answer"):
        return "Undo left the Edit in the Answer"
    wide.close()
    narrow = browser.new_page(viewport={"width": 390, "height": 844})
    narrow.on("request", lambda r: sent.append(r.url) if not r.url.startswith(("file:", "data:")) else None)
    narrow.goto(page_file.as_uri())
    for pid in page_ids(narrow):
        narrow.click(f'[data-goto="{pid}"]')
        width = narrow.evaluate("document.documentElement.scrollWidth")
        if width > 390:
            return f"page {pid}: {width} px wide at 390 px"
        stray = narrow.evaluate(STRAY_BUTTONS_JS)
        if stray:
            return f"page {pid}: {stray} buttons outside a node card, the header and the bottom bar at 390 px"
    narrow.close()
    if sent:
        return f"requests left the file: {sent[:3]}"
    return None


def layout_dir(d):
    from playwright.sync_api import sync_playwright
    files = sorted(pathlib.Path(d).glob("*.json"))
    if not files:
        print("refused: no plan files in " + d)
        return 1
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        browser = pw.chromium.launch()
        for f in files:
            fact = measure(browser, f, tmp)
            if fact:
                print(f"refused: {f.name}: {fact}")
                return 1
            print(f"{f.name}: no Answer box, Options right of the question, fits 390 px, buttons on cards or bars, edit and undo, no network")
        browser.close()
    print(f"layout ok {len(files)}")
    return 0


def items(x):
    """Every Part under X, through its Options and follow-up, the same walk as the page's."""
    out = []
    for p in x.get("parts", []):
        out += [p] + items(p)
    if tree_plan.is_decision(x):
        for o in tree_plan.options(x):
            out += items(o)
    if x.get("then"):
        out += items(x["then"])
    return out


def matters_most(ids, decisions):
    """The most risks under it, then the most Parts under its Options, then the first."""
    def key(d):
        risks = sum(1 for p in items(ids[d]) if p.get("kind") == "risk")
        return (risks, sum(len(items(o)) for o in tree_plan.options(ids[d])))
    return max(decisions, key=key) if decisions else None  # max keeps the first of equals


def views(browser, plan_path, out_dir):
    """The strategies of #1015 on one example; returns the first fact that fails, or None."""
    plan = tree_plan.load_file(plan_path)
    text = build(plan_path)
    if "<img" in text or any(not text[i + 4:].startswith("data:") for i in range(len(text)) if text.startswith("url(", i)):
        return "the page holds an image"
    page_file = pathlib.Path(out_dir) / (pathlib.Path(plan_path).stem + ".html")
    page_file.write_text(text, encoding="utf-8")
    ids = tree_plan.index(plan)
    decisions = [i for i, p in ids.items() if tree_plan.is_decision(p)]
    page = browser.new_page(viewport={"width": 1200, "height": 900})
    page.goto(page_file.as_uri())
    shown = "section:not([hidden])"
    for pid in page_ids(page):
        page.click(f'[data-goto="{pid}"]')
        wide = page.evaluate(f"""() => [...document.querySelectorAll('{shown} .mock')]
          .filter(m => m.getBoundingClientRect().width > m.closest('.node').getBoundingClientRect().width + 0.5).length""")
        if wide:
            return f"page {pid}: {wide} mockup frames wider than their card"
    marked = set(page.eval_on_selector_all("[data-most]", "els => els.map(e => e.dataset.most)"))
    if decisions and marked != {matters_most(ids, decisions)}:
        return f"matters most marks {sorted(marked)}, expected {matters_most(ids, decisions)}"
    if any(not t.split("·", 1)[-1].strip() for t in page.eval_on_selector_all(".most", "els => els.map(e => e.textContent)")):
        return "a matters-most mark names no reason"
    if decisions:
        page.click('[data-goto="plan"]')
        rows = page.eval_on_selector_all(f"{shown} .crow", "els => els.map(e => [e.dataset.row, e.textContent])")
        if [r[0] for r in rows] != decisions:
            return f"Your choices rows {[r[0] for r in rows]}, expected {decisions}"
        for (rid, t) in rows:
            if ids[rid]["pick"]["text"] not in t:
                return f"Your choices row {rid} lacks the Agent's pick"
        first = decisions[0]
        opts = tree_plan.options(ids[first])
        k = 2 if len(opts) >= 2 else 1
        page.click(f'[data-goto="{first}"]')
        page.keyboard.press(str(k))
        if opts[k - 1].get("then"):
            page.keyboard.press("1")
        stubs = page.locator(f"{shown} .stub")
        if stubs.count() != 1:
            return f"a pick left {stubs.count()} stubs, not one"
        stubs.click()
        if page.locator(f"{shown} .onode").count() != len(opts) + 1:
            return "the stub did not bring back every Option"
        page.click('[data-goto="plan"]')
        row = page.text_content(f'{shown} .crow[data-row="{first}"]')
        if opts[k - 1]["text"] not in row:
            return f"Your choices row {first} did not follow the pick"
    else:
        page.click('[data-goto="plan"]')
    target = next((i for i in ids if ids[i].get("parts") or ids[i].get("source")), "1")
    keep = {target, target.rsplit(".", 1)[0] if "." in target else None}
    keep |= {f"{target}.{n}" for n in range(1, len(ids[target].get("parts", [])) + 1)}
    keep |= {i for i in ids if ids[target].get("source") and ids[i].get("source") == ids[target]["source"]}
    page.click(f'{shown} [data-id="{target}"] > div > .pid')
    faded_now = set(page.eval_on_selector_all(f"{shown} .part.unfocus", "els => els.map(e => e.dataset.id)"))
    if faded_now != set(ids) - keep:
        return f"focus on {target} faded {sorted(faded_now)}, expected {sorted(set(ids) - keep)}"
    page.keyboard.press("Escape")
    if page.locator(f"{shown} .part.unfocus").count():
        return "Esc left cards faded"
    parent = next((i for i in ids if ids[i].get("parts")), None)
    if parent:
        page.click(f'{shown} [data-id="{parent}"] .fold')
        if page.locator(f'{shown} [data-id^="{parent}."]').count():
            return f"a fold of {parent} left its children shown"
        page.click(f'{shown} [data-id="{parent}"] .fold')
        if not page.locator(f'{shown} [data-id^="{parent}."]').count():
            return f"an unfold of {parent} left its children hidden"
    page.close()
    return None


def strategies_dir(d):
    from playwright.sync_api import sync_playwright
    files = sorted(pathlib.Path(d).glob("*.json"))
    if not files:
        print("refused: no plan files in " + d)
        return 1
    mockups = sum(1 for f in files for p in items(tree_plan.load_file(f)) if p.get("kind") == "mockup")
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        browser = pw.chromium.launch()
        for f in files:
            fact = views(browser, f, tmp)
            if fact:
                print(f"refused: {f.name}: {fact}")
                return 1
            print(f"{f.name}: Your choices follows the pick, one stub restores the Options, focus and Esc, fold and unfold, mockups fit, one Decision matters most, no image")
        browser.close()
    if not mockups:
        print("refused: the examples hold no mockup")
        return 1
    print(f"strategies ok {len(files)}")
    return 0


def capture(page_html, out):
    from playwright.sync_api import sync_playwright
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    uri = pathlib.Path(page_html).resolve().as_uri()
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        page.goto(uri)
        page.screenshot(path=str(out / "1200-load.png"), full_page=True)
        page.keyboard.press("2")
        page.screenshot(path=str(out / "1200-pick-2.png"), full_page=True)
        page.hover("text=Margin drops to 41%")
        page.screenshot(path=str(out / "1200-hover-risk.png"), full_page=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(uri)
        page.screenshot(path=str(out / "390-load.png"), full_page=True)
        browser.close()
    print(f"wrote 1200-load.png, 1200-pick-2.png, 1200-hover-risk.png and 390-load.png into {out}")
    return 0


def capture_all(page_html, out):
    """Each page as a reader first meets it: no key pressed, no hover."""
    from playwright.sync_api import sync_playwright
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    uri = pathlib.Path(page_html).resolve().as_uri()
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        page.goto(uri)
        names = []
        for i, pid in enumerate(page_ids(page), 1):
            page.click(f'[data-goto="{pid}"]')
            page.mouse.move(0, 0)
            kind = "plan" if pid == "plan" else "decision"
            # Screens as a reader scrolls them, overlapping, since a full-page shot draws the fixed bar over the middle.
            height = page.evaluate("document.documentElement.scrollHeight")
            for k, top in enumerate(range(0, max(height - 900, 0) + 1, 700), 1):
                page.evaluate(f"window.scrollTo(0, {top})")
                name = f"page-{i}-{kind}-{k}.png"
                page.screenshot(path=str(out / name))
                names.append(name)
            if (height - 900) % 700 and height > 900:
                page.evaluate(f"window.scrollTo(0, {height})")
                name = f"page-{i}-{kind}-{k + 1}.png"
                page.screenshot(path=str(out / name))
                names.append(name)
            page.evaluate("window.scrollTo(0, 0)")
        browser.close()
    print(f"wrote {len(names)} pages into {out}: {' '.join(names)}")
    return 0


def check_dir(d):
    from playwright.sync_api import sync_playwright
    files = sorted(pathlib.Path(d).glob("*.json"))
    if not files:
        print("refused: no plan files in " + d)
        return 1
    n = 0
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(permissions=["clipboard-read", "clipboard-write"])
        for f in files:
            try:
                how = drive(ctx, f, tmp)
            except Exception as e:  # report every failing example by name
                print(f"refused: {f.name}: {e}")
                return 1
            print(f"{f.name}: page built, later Parts faded, answer read from the {how}, next plan passes the checker")
            n += 1
        browser.close()
    print(f"ok {n}")
    return 0


def main(args):
    if len(args) == 2 and args[0] == "--check":
        return check_dir(args[1])
    if len(args) == 2 and args[0] == "--layout":
        return layout_dir(args[1])
    if len(args) == 2 and args[0] == "--strategies":
        return strategies_dir(args[1])
    if len(args) == 3 and args[0] == "--capture-all":
        return capture_all(args[1], args[2])
    if len(args) == 3 and args[0] == "--capture":
        return capture(args[1], args[2])
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        pathlib.Path(args[1]).write_text(build(args[0]), encoding="utf-8")
    except (tree_plan.PlanError, OSError) as e:
        print(f"refused: {e}")
        return 1
    print(f"wrote {args[1]}: one page, open it, answer each Decision, press Copy answer and paste the text back")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

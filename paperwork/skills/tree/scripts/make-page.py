#!/usr/bin/env python3
"""Build the answer page of a tree plan.

usage: make-page.py PLAN.json OUT.html     one self-contained page; refused when the plan fails the checker
       make-page.py --check DIR            drive every DIR/X.json in headless Chromium and print "ok N"
       make-page.py --layout DIR           measure every DIR/X.json's page as a tree and print "layout ok N"
       make-page.py --strategies DIR       drive every DIR/X.json's views (choices, stub, focus, fold, mockup, matters most)
                                           and print "strategies ok N"
       make-page.py --capture PAGE.html DIR  write the four review PNGs of a built page into DIR
       make-page.py --capture-all PAGE.html DIR  write every page of a built page, untouched, at 1200 px into DIR
       make-page.py --capture-picked PAGE.html DIR  write each Decision page after its first Option is picked
                                           (every call but the first needs playwright: uv run --with playwright==1.64.1 python3 make-page.py ...)
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
    errors = tree_plan.check(plan)
    if errors:
        raise tree_plan.PlanError(*errors[0])
    # "</" would end the script element early inside the embedded JSON.
    data = json.dumps(plan, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8")
    return (page.replace("__TITLE__", html.escape(plan["title"])).replace("__STAMP__", tree_plan.stamp(plan))
            .replace("__PLAN__", data))


def strikeable(plan):
    """First non-Decision Part with no Decision inside it, so the pick still counts."""
    ids = tree_plan.index(plan)
    for part_id, part in ids.items():
        inside = [inside_part for other_id, inside_part in ids.items() if other_id.startswith(part_id + ".")]
        if not tree_plan.is_decision(part) and not any(tree_plan.is_decision(inside_part) for inside_part in inside):
            return part_id
    return None


def later_ids(ids, decisions, answered):
    """The Parts the page must fade: after the first open Decision, outside its subtree."""
    open_decision = next((decision_id for decision_id in decisions if decision_id not in answered), None)
    if open_decision is None:
        return set()
    order = list(ids)
    return {part_id for part_id in order[order.index(open_decision) + 1:] if not part_id.startswith(open_decision + ".")}


def faded(page):
    return set(page.eval_on_selector_all(".part.later", "els => els.map(e => e.dataset.id)"))


def card_action(page, part_id, label):
    page.hover(f'[data-id="{part_id}"]')
    page.click(f'[data-id="{part_id}"] > .acts button:text-is("{label}")')


def drive(browser_context, plan_path, out_dir):
    plan = tree_plan.load_file(plan_path)
    page_file = pathlib.Path(out_dir) / (pathlib.Path(plan_path).stem + ".html")
    page_file.write_text(build(plan_path), encoding="utf-8")
    page = browser_context.new_page()
    errors = []
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(page_file.as_uri())
    ids = tree_plan.index(plan)
    decisions = [part_id for part_id, part in ids.items() if tree_plan.is_decision(part)]
    if faded(page) != later_ids(ids, decisions, set()):
        raise AssertionError(f"faded on load {sorted(faded(page))}, expected {sorted(later_ids(ids, decisions, set()))}")
    if decisions:
        first = ids[decisions[0]]
        options = tree_plan.options(first)
        option_number = 2 if len(options) >= 2 else 1
        page.keyboard.press(str(option_number))
        follow_up = options[option_number - 1].get("then")
        if follow_up:
            page.keyboard.press("2" if len(tree_plan.options(follow_up)) >= 2 else "1")
    if decisions and faded(page) != later_ids(ids, decisions, {decisions[0]}):
        raise AssertionError(f"faded after the first pick {sorted(faded(page))}, expected {sorted(later_ids(ids, decisions, {decisions[0]}))}")
    target = strikeable(plan)
    # Outside the struck subtree, since a struck Part's descendants add no lines.
    commented = next((part_id for part_id in ids if not (target and (part_id == target or part_id.startswith(target + ".")))
                      and not tree_plan.is_decision(ids[part_id])), None) or decisions[0]
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
    verbs = {entry[2] for entry in entries}
    need = {"comment"} | ({"struck"} if target else set())
    if not need <= verbs:
        raise AssertionError(f"answer lacks {sorted(need - verbs)}: {text!r}")
    if decisions and not ({"pick", "other"} & verbs):
        raise AssertionError(f"answer has no pick: {text!r}")
    next_plan = tree_plan.apply_answer(plan, entries)
    next_errors = tree_plan.check(next_plan)
    if next_errors:
        raise AssertionError(f"next plan refused: {next_errors[0]}")
    return how


ANSWER_BOX_SCRIPT = """() => { let m = 0;
  for (const e of document.querySelectorAll('body *')) {
    const own = typeof e.value === 'string' ? e.value
      : [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('');
    if (own.includes('# Answer:') && e.getClientRects().length) m = Math.max(m, e.getBoundingClientRect().height);
  } return Math.round(m); }"""
STRAY_BUTTONS_SCRIPT = """() => [...document.querySelectorAll('button')]
  .filter(b => b.getClientRects().length && !b.closest('.node, header, #bar')).length"""
OPTIONS_LEFT_SCRIPT = """() => { const s = document.querySelector('section:not([hidden])');
  const q = s.querySelector('.qcard').getBoundingClientRect().right;
  return [...s.querySelectorAll('.onode')].filter(o => o.getBoundingClientRect().left < q).length; }"""

# A long Korean sentence in every card's text, since a short one hides a tool row that covers the second line.
LONG_KOREAN = "이 항목은 카드 안에서 여러 줄로 이어지도록 일부러 길게 쓴 한국어 문장이며 도구 버튼이 글자 위에 겹치지 않는지 확인하는 데 쓰입니다 " * 2
STRETCH_SCRIPT = """(text) => { for (const e of document.querySelectorAll('.ptext, .qtext')) {
  const n = [...e.childNodes].find(c => c.nodeType === 3); if (n) n.textContent = text; } }"""
# The tools of a card (.acts) against every text run of that card.
OVERLAP_SCRIPT = """() => { const bad = [];
  for (const card of document.querySelectorAll('section:not([hidden]) .node')) {
    const acts = card.querySelector(':scope > .acts'); if (!acts) continue;
    const a = acts.getBoundingClientRect();
    const walk = document.createTreeWalker(card, NodeFilter.SHOW_TEXT); let n;
    while ((n = walk.nextNode())) {
      if (acts.contains(n) || !n.textContent.trim()) continue;
      const range = document.createRange(); range.selectNodeContents(n);
      for (const q of range.getClientRects())
        if (q.width && q.height && q.left < a.right - .5 && q.right > a.left + .5 && q.top < a.bottom - .5 && q.bottom > a.top + .5)
          bad.push(card.dataset.id || card.dataset.card || card.className);
    } }
  return [...new Set(bad)]; }"""
# The page's own labels, with the plan's words cut out, hold no middle dot, no all-caps and no uppercase transform.
LABELS_SCRIPT = """(words) => { const bad = [];
  words.sort((x, y) => y.length - x.length);
  for (const e of document.body.querySelectorAll('*')) {
    if (['SCRIPT', 'STYLE', 'TEXTAREA'].includes(e.tagName)) continue;
    if (getComputedStyle(e).textTransform === 'uppercase') bad.push('uppercase transform on .' + e.className);
    let own = [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join(' ');
    for (const w of words) own = own.split(w).join(' ');
    if (own.includes('\u00b7')) bad.push('middle dot in ' + JSON.stringify(own.trim()));
    if (/[A-Z]{3,}/.test(own) && own === own.toUpperCase()) bad.push('all caps ' + JSON.stringify(own.trim()));
  }
  return bad; }"""
PICK_STYLE_SCRIPT = """() => { const o = document.querySelector('section:not([hidden]) [data-option="1"]'), s = getComputedStyle(o);
  return { weight: +s.fontWeight, shadow: s.boxShadow, border: s.borderStyle + ' ' + s.borderTopColor + ' ' + s.borderTopWidth, mark: (o.querySelector('.mark') || {}).textContent || '' }; }"""


def plan_words(node, words=None):
    """Every string of the plan, and the names of each source, for the labels probe to cut out."""
    words = set() if words is None else words
    if isinstance(node, str):
        if len(node) > 1:
            words.add(node)
            words.update(name for name in node.split(" \u00b7 ") if len(name) > 1)
    elif isinstance(node, dict):
        for value in node.values():
            plan_words(value, words)
    elif isinstance(node, list):
        for value in node:
            plan_words(value, words)
    return words


def check_pick_look(browser, page_file, first):
    """The Agent's pick is faint until the owner answers; the owner's pick is heavier."""
    page = browser.new_page(viewport={"width": 1200, "height": 900})
    page.goto(page_file.as_uri())
    page.click(f'[data-goto="{first}"]')
    before = page.evaluate(PICK_STYLE_SCRIPT)
    page.keyboard.press("1")
    after = page.evaluate(PICK_STYLE_SCRIPT)
    page.close()
    if before["shadow"] != "none" or after["shadow"] == "none":
        return f"page {first}: the suggested and the picked Option show the same ring ({before['shadow']!r}, {after['shadow']!r})"
    if before["border"] == after["border"] or before["weight"] >= after["weight"]:
        return f"page {first}: the picked Option is not bolder or bordered apart from the suggested one ({before}, {after})"
    if before["mark"] != "Agent's pick" or after["mark"] != "Your pick":
        return f"page {first}: the marks read {before['mark']!r} then {after['mark']!r}"
    return None


def page_ids(page):
    return page.eval_on_selector_all("#pager [data-goto]", "els => els.map(e => e.dataset.goto)")


def measure(browser, plan_path, out_dir):
    """The facts that make the page a tree; returns the first that fails, or None."""
    page_file = pathlib.Path(out_dir) / (pathlib.Path(plan_path).stem + ".html")
    page_file.write_text(build(plan_path), encoding="utf-8")
    sent = []
    wide = browser.new_page(viewport={"width": 1200, "height": 900})
    wide.on("request", lambda request: sent.append(request.url) if not request.url.startswith(("file:", "data:")) else None)
    wide.goto(page_file.as_uri())
    words = sorted(plan_words(tree_plan.load_file(plan_path)))
    box = wide.evaluate(ANSWER_BOX_SCRIPT)
    if box:
        return f"the Answer text shows in a box {box} px tall"
    for page_id in page_ids(wide):
        wide.click(f'[data-goto="{page_id}"]')
        labels = wide.evaluate(LABELS_SCRIPT, words)
        if labels:
            return f"page {page_id}: {labels[0]}"
        wide.evaluate(STRETCH_SCRIPT, LONG_KOREAN)
        covered = wide.evaluate(OVERLAP_SCRIPT)
        if covered:
            return f"page {page_id}: the tools of card {covered[0]} cover its text at 1200 px"
        stray = wide.evaluate(STRAY_BUTTONS_SCRIPT)
        if stray:
            return f"page {page_id}: {stray} buttons outside a node card, the header and the bottom bar"
        if page_id != "plan" and wide.evaluate(OPTIONS_LEFT_SCRIPT):
            return f"page {page_id}: an Option card starts left of the question card's right edge at 1200 px"
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
    decisions = [part_id for part_id, part in tree_plan.index(tree_plan.load_file(plan_path)).items() if tree_plan.is_decision(part)]
    if decisions:
        fact = check_pick_look(browser, page_file, decisions[0])
        if fact:
            return fact
    narrow = browser.new_page(viewport={"width": 390, "height": 844})
    narrow.on("request", lambda request: sent.append(request.url) if not request.url.startswith(("file:", "data:")) else None)
    narrow.goto(page_file.as_uri())
    for page_id in page_ids(narrow):
        narrow.click(f'[data-goto="{page_id}"]')
        narrow.evaluate(STRETCH_SCRIPT, LONG_KOREAN)
        covered = narrow.evaluate(OVERLAP_SCRIPT)
        if covered:
            return f"page {page_id}: the tools of card {covered[0]} cover its text at 390 px"
        width = narrow.evaluate("document.documentElement.scrollWidth")
        if width > 390:
            return f"page {page_id}: {width} px wide at 390 px"
        stray = narrow.evaluate(STRAY_BUTTONS_SCRIPT)
        if stray:
            return f"page {page_id}: {stray} buttons outside a node card, the header and the bottom bar at 390 px"
    narrow.close()
    if sent:
        return f"requests left the file: {sent[:3]}"
    return None


def layout_dir(directory):
    from playwright.sync_api import sync_playwright
    files = sorted(pathlib.Path(directory).glob("*.json"))
    if not files:
        print("refused: no plan files in " + directory)
        return 1
    with tempfile.TemporaryDirectory() as temporary_directory, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for file in files:
            fact = measure(browser, file, temporary_directory)
            if fact:
                print(f"refused: {file.name}: {fact}")
                return 1
            print(f"{file.name}: no Answer box, Options right of the question, tools clear of the text, plain labels, pick looks apart, fits 390 px, buttons on cards or bars, edit and undo, no network")
        browser.close()
    print(f"layout ok {len(files)}")
    return 0


def items(node):
    """Every Part under X, through its Options and follow-up, the same walk as the page's."""
    found = []
    for part in node.get("parts", []):
        found += [part] + items(part)
    if tree_plan.is_decision(node):
        for option in tree_plan.options(node):
            found += items(option)
    if node.get("then"):
        found += items(node["then"])
    return found


def most_key(ids, decision_id):
    """A Decision's risks under it, then the Parts under its Options."""
    risks = sum(1 for part in items(ids[decision_id]) if part.get("kind") == "risk")
    return (risks, sum(len(items(option)) for option in tree_plan.options(ids[decision_id])))


def matters_most(ids, decisions):
    """The most risks under it, then the most Parts under its Options, then the first."""
    return max(decisions, key=lambda decision_id: most_key(ids, decision_id)) if decisions else None  # max keeps the first of equals


def most_reason(ids, decisions):
    """The opening words of the matters-most reason, by the rule that decided it."""
    best = most_key(ids, matters_most(ids, decisions))
    others = [most_key(ids, decision_id) for decision_id in decisions if decision_id != matters_most(ids, decisions)]
    same = [key for key in others if key[0] == best[0]]
    if not same:
        return "More risks than any other Decision"
    if all(key[1] < best[1] for key in same):
        return "As many risks as the most" if best[0] else "No Decision has more risks"
    return "It ties with another Decision"


def views(browser, plan_path, out_dir):
    """The strategies of #1015 on one example; returns the first fact that fails, or None."""
    plan = tree_plan.load_file(plan_path)
    text = build(plan_path)
    if "<img" in text or any(not text[i + 4:].startswith("data:") for i in range(len(text)) if text.startswith("url(", i)):
        return "the page holds an image"
    page_file = pathlib.Path(out_dir) / (pathlib.Path(plan_path).stem + ".html")
    page_file.write_text(text, encoding="utf-8")
    ids = tree_plan.index(plan)
    decisions = [part_id for part_id, part in ids.items() if tree_plan.is_decision(part)]
    page = browser.new_page(viewport={"width": 1200, "height": 900})
    page.goto(page_file.as_uri())
    shown = "section:not([hidden])"
    for page_id in page_ids(page):
        page.click(f'[data-goto="{page_id}"]')
        wide = page.evaluate(f"""() => [...document.querySelectorAll('{shown} .mock')]
          .filter(m => m.getBoundingClientRect().width > m.closest('.node').getBoundingClientRect().width + 0.5).length""")
        if wide:
            return f"page {page_id}: {wide} mockup frames wider than their card"
    marked = set(page.eval_on_selector_all("[data-most]", "els => els.map(e => e.dataset.most)"))
    if decisions and marked != {matters_most(ids, decisions)}:
        return f"matters most marks {sorted(marked)}, expected {matters_most(ids, decisions)}"
    if any(not mark_text.split(":", 1)[-1].strip() for mark_text in page.eval_on_selector_all(".most", "els => els.map(e => e.textContent)")):
        return "a matters-most mark names no reason"
    reasons = page.eval_on_selector_all(".most-why", "els => els.map(e => e.textContent)")
    if decisions and not all(reason.removeprefix("Why it matters most").startswith(most_reason(ids, decisions)) for reason in reasons):
        return f"the matters-most reason does not open with {most_reason(ids, decisions)!r}"
    for decision_id in decisions:
        kids = ids[decision_id].get("parts", [])
        opened = next((part for part in kids if part.get("parts")), None)
        if opened is None:
            continue
        page.click(f'[data-goto="{decision_id}"]')
        toggle = page.locator(f"{shown} .ctx-toggle[aria-expanded]").nth(0)
        if toggle.text_content() != "\u25b8" or page.locator(f"{shown} .ctx-kids").count():
            return f"page {decision_id}: a context line with Parts starts open"
        toggle.click()
        toggle = page.locator(f"{shown} .ctx-toggle[aria-expanded]").nth(0)
        sourced = sum(1 for part in opened["parts"] if part.get("source"))
        if toggle.text_content() != "\u25be" or page.locator(f"{shown} .ctx-kids > .ctx").count() != len(opened["parts"]):
            return f"page {decision_id}: a click on a context line did not open its {len(opened['parts'])} Parts"
        if page.locator(f"{shown} .ctx-kids .chip").count() != sourced:
            return f"page {decision_id}: the opened Parts show {page.locator(f'{shown} .ctx-kids .chip').count()} source chips, expected {sourced}"
        toggle.click()
        if page.locator(f"{shown} .ctx-kids").count():
            return f"page {decision_id}: a second click did not close the context line"
    if decisions:
        page.click('[data-goto="plan"]')
        rows = page.eval_on_selector_all(f"{shown} .crow", "els => els.map(e => [e.dataset.row, e.textContent])")
        if [choice_row[0] for choice_row in rows] != decisions:
            return f"Your choices rows {[choice_row[0] for choice_row in rows]}, expected {decisions}"
        for (row_id, row_text) in rows:
            if ids[row_id]["pick"]["text"] not in row_text:
                return f"Your choices row {row_id} lacks the Agent's pick"
        first = decisions[0]
        options = tree_plan.options(ids[first])
        option_number = 2 if len(options) >= 2 else 1
        page.click(f'[data-goto="{first}"]')
        page.keyboard.press(str(option_number))
        if options[option_number - 1].get("then"):
            page.keyboard.press("1")
        stubs = page.locator(f"{shown} .stub")
        if stubs.count() != 1:
            return f"a pick left {stubs.count()} stubs, not one"
        stubs.click()
        if page.locator(f"{shown} .onode").count() != len(options) + 1:
            return "the stub did not bring back every Option"
        page.click('[data-goto="plan"]')
        row = page.text_content(f'{shown} .crow[data-row="{first}"]')
        if options[option_number - 1]["text"] not in row:
            return f"Your choices row {first} did not follow the pick"
    else:
        page.click('[data-goto="plan"]')
    target = next((part_id for part_id in ids if ids[part_id].get("parts") or ids[part_id].get("source")), "1")
    keep = {target, target.rsplit(".", 1)[0] if "." in target else None}
    keep |= {f"{target}.{n}" for n in range(1, len(ids[target].get("parts", [])) + 1)}
    keep |= {part_id for part_id in ids if ids[target].get("source") and ids[part_id].get("source") == ids[target]["source"]}
    page.click(f'{shown} [data-id="{target}"] > div > .pid')
    faded_now = set(page.eval_on_selector_all(f"{shown} .part.unfocus", "els => els.map(e => e.dataset.id)"))
    if faded_now != set(ids) - keep:
        return f"focus on {target} faded {sorted(faded_now)}, expected {sorted(set(ids) - keep)}"
    page.keyboard.press("Escape")
    if page.locator(f"{shown} .part.unfocus").count():
        return "Esc left cards faded"
    parent = next((part_id for part_id in ids if ids[part_id].get("parts")), None)
    if parent:
        page.click(f'{shown} [data-id="{parent}"] .fold')
        if page.locator(f'{shown} [data-id^="{parent}."]').count():
            return f"a fold of {parent} left its children shown"
        page.click(f'{shown} [data-id="{parent}"] .fold')
        if not page.locator(f'{shown} [data-id^="{parent}."]').count():
            return f"an unfold of {parent} left its children hidden"
    page.close()
    return None


def strategies_dir(directory):
    from playwright.sync_api import sync_playwright
    files = sorted(pathlib.Path(directory).glob("*.json"))
    if not files:
        print("refused: no plan files in " + directory)
        return 1
    mockups = sum(1 for file in files for part in items(tree_plan.load_file(file)) if part.get("kind") == "mockup")
    with tempfile.TemporaryDirectory() as temporary_directory, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for file in files:
            fact = views(browser, file, temporary_directory)
            if fact:
                print(f"refused: {file.name}: {fact}")
                return 1
            print(f"{file.name}: Your choices follows the pick, one stub restores the Options, focus and Esc, fold and unfold, mockups fit, one Decision matters most, no image, a context line opens on a click")
        browser.close()
    if not mockups:
        print("refused: the examples hold no mockup")
        return 1
    if not any(part.get("parts") for file in files for decision in items(tree_plan.load_file(file)) if tree_plan.is_decision(decision) for part in decision.get("parts", [])):
        print("refused: the examples hold no context line with Parts of its own")
        return 1
    print(f"strategies ok {len(files)}")
    return 0


def capture(page_html, out_dir):
    from playwright.sync_api import sync_playwright
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    uri = pathlib.Path(page_html).resolve().as_uri()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        page.goto(uri)
        page.screenshot(path=str(out_dir / "1200-load.png"), full_page=True)
        page.keyboard.press("2")
        page.screenshot(path=str(out_dir / "1200-pick-2.png"), full_page=True)
        page.hover("text=Margin drops to 41%")
        page.screenshot(path=str(out_dir / "1200-hover-risk.png"), full_page=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(uri)
        page.screenshot(path=str(out_dir / "390-load.png"), full_page=True)
        browser.close()
    print(f"wrote 1200-load.png, 1200-pick-2.png, 1200-hover-risk.png and 390-load.png into {out_dir}")
    return 0


def screens(page, out_dir, stem):
    """The page as a reader scrolls it, in overlapping screens, since a full-page shot draws the fixed bar over the middle."""
    names = []
    height = page.evaluate("document.documentElement.scrollHeight")
    tops = list(range(0, max(height - 900, 0) + 1, 700))
    if height > 900 and (height - 900) % 700:
        tops.append(height - 900)
    for index, top in enumerate(tops, 1):
        page.evaluate(f"window.scrollTo(0, {top})")
        names.append(f"{stem}-{index}.png")
        page.screenshot(path=str(out_dir / names[-1]))
    page.evaluate("window.scrollTo(0, 0)")
    return names


def capture_all(page_html, out_dir, picked=False):
    """Each page as a reader first meets it, no key pressed and no hover; with PICKED, each Decision after its first Option."""
    from playwright.sync_api import sync_playwright
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    uri = pathlib.Path(page_html).resolve().as_uri()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        page.goto(uri)
        names = []
        for i, page_id in enumerate(page_ids(page), 1):
            if picked and page_id == "plan":
                continue
            page.click(f'[data-goto="{page_id}"]')
            if picked:
                page.keyboard.press("1")
                page.keyboard.press("1")
            page.mouse.move(0, 0)
            kind = "plan" if page_id == "plan" else "decision"
            names += screens(page, out_dir, f"page-{i}-{kind}" + ("-picked" if picked else ""))
        browser.close()
    print(f"wrote {len(names)} pages into {out_dir}: {' '.join(names)}")
    return 0


def check_dir(directory):
    from playwright.sync_api import sync_playwright
    files = sorted(pathlib.Path(directory).glob("*.json"))
    if not files:
        print("refused: no plan files in " + directory)
        return 1
    n = 0
    with tempfile.TemporaryDirectory() as temporary_directory, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(permissions=["clipboard-read", "clipboard-write"])
        for file in files:
            try:
                how = drive(context, file, temporary_directory)
            except Exception as e:  # report every failing example by name
                print(f"refused: {file.name}: {e}")
                return 1
            print(f"{file.name}: page built, later Parts faded, answer read from the {how}, next plan passes the checker")
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
    if len(args) == 3 and args[0] == "--capture-picked":
        return capture_all(args[1], args[2], picked=True)
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

#!/usr/bin/env python3
"""Build the answer page of a tree plan.

usage: make-page.py PLAN.json OUT.html   one self-contained page; refused when the plan fails the checker
       make-page.py --check DIR          drive every DIR/X.json in headless Chromium and print "ok N"
                                         (needs playwright: uv run --with playwright==1.64.1 python3 make-page.py --check DIR)
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
    if target:
        page.click(f'[data-id="{target}"] > .row .actions button:text-is("Strike")')
        page.fill(".ed-strike", "not needed")
        page.keyboard.press("Enter")
    page.click(f'[data-id="{commented}"] > .row .actions button:text-is("Comment")')
    page.fill(".ed-comment", "checked by the page probe")
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
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        pathlib.Path(args[1]).write_text(build(args[0]), encoding="utf-8")
    except (tree_plan.PlanError, OSError) as e:
        print(f"refused: {e}")
        return 1
    print(f"wrote {args[1]}: one page, answer lines appear in its Answer box; open it, answer, press Copy Answer")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

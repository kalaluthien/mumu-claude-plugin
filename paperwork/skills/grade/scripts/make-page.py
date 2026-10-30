#!/usr/bin/env python3
"""Build the HTML report card of one target from its rubric and its grades.

usage: make-page.py RUBRIC.json GRADES.json OUT.html   one self-contained page; refused when they break check-rubric.py's rules
       make-page.py --check DIR [PNG_DIR]              measure the page of every DIR/X/ in headless Chromium, printing "ok N", then
                                                         "<fact> ok" per fact; PNG_DIR takes pictures (needs playwright)
"""
import html
import json
import pathlib
import re
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))

from page import frame  # noqa: E402
from rubric.check import Refused, errors, grades_problems, line, read_rubric  # noqa: E402
from rubric.verdict import gaps, needs_person, rating, split, status  # noqa: E402

ASSETS = pathlib.Path(__file__).resolve().parents[1] / "assets"
URL = re.compile(r"https?://\S+")
FOLD_STATE = "[...document.querySelectorAll('details')].map(d => d.open)"
FOLD_CHANGE = "(d => { d.open = !d.open; })(document.querySelector('details'))"
PAGE_FACTS = ("first screen", "run counts", "needs a person", "evidence folded", "grader text", "empty fixes", "copy pairs", "status tags", "fix once",
              "no response path", "split rule", "outside fold")
GROUPS = (("Not met", "failed", ("✗ Not met",), "No criterion failed with every run agreeing."),
          ("Not sure", "open", ("? Not sure", "? Not settled"), "The runs agreed on every criterion."),
          ("Not judged", "open", ("? Not judged",), "Every criterion was judged."),
          ("Met", "passed", ("✓ Met",), "No criterion was met."))


def load(rubric_path, grades_path):
    rubric, rubric_bytes = read_rubric(rubric_path)
    grades = json.loads(pathlib.Path(grades_path).read_text(encoding="utf-8"))
    if wrong := errors(grades_problems(rubric, rubric_bytes, grades)):
        raise Refused(f"{rubric_path}: {line(wrong[0])}")
    return rubric, grades


def escape(text):
    return html.escape(str(text))


def linked(text):
    out, last = [], 0
    for match in URL.finditer(text):
        url = match.group().rstrip(".,;)")
        out += [escape(text[last:match.start()]), f'<a href="{escape(url)}">{escape(url)}</a>']
        last = match.start() + len(url)
    return "".join(out + [escape(text[last:])])


def word(criterion, grade):
    state = status(criterion, grade)
    if state in ("not judged", "not settled"):
        return f"? {state.capitalize()}"
    return "? Not sure" if split(grade) else "✓ Met" if state == "met" else "✗ Not met"


def counted(n, one, many=None):
    return f"{n} {one if n == 1 else many or one + 's'}"


def rows(rubric, grades):
    return [(criterion, grades["grades"][criterion["id"]]) for criterion in sorted(rubric["criteria"], key=lambda criterion: not criterion.get("critical"))]


def critical_tag(criterion):
    return '<span class="frame-tag fail critical">critical</span>' if criterion.get("critical") else ""


def list_item(criterion, content):
    mark = ' class="critical"' if criterion.get("critical") else ""
    return f'<li id="fix-{escape(criterion["id"])}"{mark} data-criterion="{escape(criterion["id"])}">{critical_tag(criterion)}{content}</li>'


def person_line(criterion, grade):
    why = ("Not judged: " + grade["reason"].rstrip(".") + "." if grade["met"] is None
           else f"The runs disagreed, {grade['runs'].count(1)} of {len(grade['runs'])} said met, and I could not settle it.")
    place = grade.get("where") or next((item["where"] for item in grade.get("items", []) if item.get("where")), "the target")
    fix = f' If it fails: {linked(grade["fix"])}' if grade.get("fix") else ""
    return list_item(criterion, f'{linked(criterion["text"])} {escape(why)} Check <span class="where">{linked(place)}</span>.{fix}')


def evidence(grade):
    places = [(item.get("quote") or f'Not found: {item["item"]}', item.get("where", "")) for item in grade.get("items", [])]
    places += [(grade["quote"], grade.get("where", ""))] if grade.get("quote") else [(f'Searched for: {grade["searched"]}', "")] if grade.get("searched") else []
    return "".join(f'<blockquote class="evidence">{linked(quote)}</blockquote>' + (f'<div class="where">quote matches {linked(where)}</div>' if where else "") for quote, where in places)


def copy_text(criterion, grade):
    out = [f'{criterion["id"]}: {word(criterion, grade)[2:]}. {criterion["text"]}']
    out += [f'  {item["item"]}: "{item.get("quote", "not found")}" {item.get("where", "")}' for item in grade.get("items", [])]
    out += [f'  "{grade["quote"]}" {grade.get("where", "")}'] if grade.get("quote") else []
    return "\n".join(out + ([f'  Fix: {grade["fix"]}'] if grade.get("fix") else []))


def card(criterion, grade, state):
    judged, runs, name = criterion["check"] == "judge", grade["runs"], escape(criterion["id"])
    dots = "".join(f'<i class="{"blank" if run is None else "yes" if run else "no"}"></i>' for run in runs)
    count = f'<span class="dots" aria-hidden="true">{dots}</span>{runs.count(1)} of {len(runs)} judge runs said met' if judged else "Decided by a program, not a judge."
    reason = f'<p class="none">{linked(grade["reason"])}</p>' if grade["met"] is None else ""
    link = f'<a href="#fix-{name}">See the list above.</a>' if grade.get("fix") or needs_person(grade) else ""
    fold = f'<details><summary>Evidence</summary>{evidence(grade)}</details>' if evidence(grade) else ""
    return (f'<article class="crit {state}" id="c-{name}" data-criterion="{name}"{f" data-runs={len(runs)}" if judged else ""} data-copy="{escape(copy_text(criterion, grade))}">'
            f'<div class="crit-head"><span class="frame-tag status">{word(criterion, grade)}</span><span class="crit-text">{critical_tag(criterion)}{linked(criterion["text"])}</span>'
            f'<span class="crit-id">{name}</span></div><div class="runs">{count}</div>{reason}{link}{fold}</article>')


def decision(critical, other):
    if critical:
        return f"Do not rely on this yet: {counted(critical, 'critical gap')}."
    if other > 1:
        return f"Close {counted(other, 'gap')} before you rely on it."
    return "Good enough to use, with 1 gap to close." if other else "Meets every criterion of its rubric."


def body(rubric, grades):
    target, subject, judge = rubric["target"], rubric["subject"], grades["judge"]
    critical, other = gaps(rubric, grades)
    person = [row for row in rows(rubric, grades) if needs_person(row[1])]
    fixes = [row for row in rows(rubric, grades) if not needs_person(row[1]) and not row[1]["met"]]
    met = sum(word(*row) == "✓ Met" for row in rows(rubric, grades))
    total = counted(len(rubric["criteria"]), "criterion", "criteria")
    out = [f'<div class="eyebrow">Report card</div><h1>{escape(target["name"])}</h1>',
           f'<div class="meta"><span>{linked(target["where"])}</span><span>version {escape(target["version"])}</span>'
           f'<span>{counted(judge["runs"], "run")} by {escape(judge["model"])}</span><span>rubric {escape(grades["rubric_sha"])}</span></div>',
           f'<section class="rating" id="rating"><p class="decision">{rating(critical, other)}: {escape(decision(critical, other))}</p>'
           f'<p>{counted(critical, "critical gap")}, {counted(other, "other gap")}, {met} of {total} met.</p>'
           '<p class="legend">The rating counts gaps, it is never a score: High has no critical gap and at most one other; Moderate more others; Low one critical gap; '
           'Critically low more. A criterion failed or not judged is a gap, and a split on a critical criterion is a gap until a person settles it.</p></section>']
    if grades["grader_text"]:
        passages = "".join(f'<li>{escape(passage["quote"])} <span class="where">{escape(passage["where"])}</span></li>' for passage in grades["grader_text"])
        out.append(f'<section class="warn" id="grader-text"><b>The target speaks to its grader.</b> The judges read this as data; check it did not sway them.<ul>{passages}</ul></section>')
    out.append('<h2 id="needs-person">Needs a person</h2>' + (f'<ol class="person">{"".join(person_line(*row) for row in person)}</ol>' if person else '<p class="none">Nothing: the runs agreed on every criterion.</p>'))
    items = "".join(list_item(criterion, f'<a href="#c-{escape(criterion["id"])}">{linked(grade["fix"])}</a>') for criterion, grade in fixes)
    out.append('<h2 id="fix-first">Fix first</h2>' + (f'<ol class="fixes">{items}</ol>' if fixes else
               f'<p class="none">{total} were checked and none failed outright. The rubric itself was not judged, and nothing outside it was checked.</p>'))
    out.append('<h2 id="criteria">Criteria</h2>')
    for title, state, words, empty in GROUPS:
        cards = [card(*row, state) for row in rows(rubric, grades) if word(*row) in words]
        out.append(f'<h3>{title}</h3>' + ("".join(cards) or f'<p class="none">{empty}</p>'))
    listed = lambda values: "<ul>" + "".join(f"<li>{linked(value)}</li>" for value in values) + "</ul>"
    out.append('<h2 id="what-was-graded">What was graded</h2><dl class="subject">'
               f'<dt>Kind</dt><dd>{escape(subject["kind"])}</dd><dt>Purpose</dt><dd>{linked(subject["purpose"])}</dd><dt>Reader</dt><dd>{linked(subject["reader"])}</dd>'
               f'<dt>Promises</dt><dd>{listed(promise["text"] + " (" + promise["where"] + ")" for promise in rubric["promises"])}</dd>'
               f'<dt>Flaws sought</dt><dd>{listed(rubric["flaws"])}</dd><dt>Criteria from</dt><dd>{listed(subject["frameworks"])}</dd></dl>')
    out.append(f'<footer>Each criterion is one yes-or-no check, and fresh judges saw only the target and the criteria. Dots show how far {counted(judge["runs"], "run")} agree, '
               'not how often they are right. “Quote matches” means the words stand at that place, not that the reading is right.</footer>')
    return "\n".join(out)


def built_page(rubric, grades):
    navigation = [("rating", "Rating"), *([("grader-text", "Text to the grader")] if grades["grader_text"] else []), ("needs-person", "Needs a person"),
                  ("fix-first", "Fix first"), ("criteria", "Criteria"), ("what-was-graded", "What was graded")]
    content = (ASSETS / "page.html").read_text(encoding="utf-8").replace("__BODY__", body(rubric, grades))
    return frame.build(f"Report card: {rubric['target']['name']}", content, navigation)


def copied_text(rubric, grades):
    return "\n".join(copy_text(*row) for _, _, words, _ in GROUPS for row in rows(rubric, grades) if word(*row) in words)


def measured(browser, url, rubric, grades):
    """Each page fact with what broke it, or Refused for a request off the file."""
    page = browser.new_page(viewport={"width": 1200, "height": 900})
    leaks = []
    page.on("request", lambda request: leaks.append(request.url) if not request.url.startswith(("file:", "data:")) else None)
    page.goto(url)
    facts = page.evaluate((ASSETS / "measure-page.js").read_text(encoding="utf-8").split("\n", 1)[1], {
        "person": [criterion["id"] for criterion, grade in rows(rubric, grades) if needs_person(grade)], "grader": len(grades["grader_text"]),
        "judged": sum(criterion["check"] == "judge" for criterion in rubric["criteria"]), "fixes": [grade["fix"] for grade in grades["grades"].values() if grade.get("fix")]})
    tags = page.locator(".frame-tag.status").count()
    page.close()
    if leaks:
        raise Refused(f"requests left for {', '.join(leaks)}")
    copied = copied_text(rubric, grades)
    bare = [criterion["id"] for criterion, grade in rows(rubric, grades) if any(value not in copied for value in (criterion["text"], grade.get("quote", ""), grade.get("fix", "")))]
    return {**facts, "copy pairs": f"copy lacks {bare}" if bare else None, "status tags": f"{tags} tags for {len(rubric['criteria'])} criteria" if tags != len(rubric["criteria"]) else None}


def fits(browser, url, name, picture_folder):
    for width in (390, 1200):
        for scheme in ("light", "dark"):
            page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=scheme)
            page.goto(url)
            if (wide := page.evaluate("document.documentElement.scrollWidth")) > width:
                raise Refused(f"{name}: {wide} px wide at {width} px, {scheme}")
            if clipped := page.eval_on_selector_all(".crit-text, .status, h1", "els => els.filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.innerText.slice(0, 30))"):
                raise Refused(f"{name}: text cut at {width} px, {scheme}: {clipped[0]}")
            if picture_folder:
                page.screenshot(path=str(pathlib.Path(picture_folder) / f"{name}-{width}-{scheme}.png"), full_page=True)
            page.close()


def check(folder, picture_folder=None):
    from playwright.sync_api import sync_playwright
    found = sorted(path for path in pathlib.Path(folder).iterdir() if (path / "rubric.json").is_file() and (path / "grades.json").is_file())
    if not found:
        raise Refused(f"{folder}: no folder holds rubric.json and grades.json")
    failures = {}
    with tempfile.TemporaryDirectory() as temporary_folder, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for example in found:
            rubric, grades = load(example / "rubric.json", example / "grades.json")
            built = pathlib.Path(temporary_folder) / f"{example.name}.html"
            built.write_text(built_page(rubric, grades), encoding="utf-8")
            kept = example / "report.html"
            if kept.is_file() and kept.read_text(encoding="utf-8") != built.read_text(encoding="utf-8"):
                raise Refused(f"{example}: report.html differs from the page its rubric and grades build; rebuild it")
            probed = frame.probe(browser, built.as_uri(), copied=copied_text(rubric, grades), change=FOLD_CHANGE, state=FOLD_STATE)
            for fact, why in {**probed, **measured(browser, built.as_uri(), rubric, grades)}.items():
                if why:
                    failures.setdefault(fact, f"{example}: {why}")
            fits(browser, built.as_uri(), example.name, picture_folder)
        all_met = {**grades, "grades": {name: {"met": 1, "runs": [1, 1, 1], "quote": "a quote", "where": "a place"} for name in grades["grades"]}}
        empty = pathlib.Path(temporary_folder) / "all-met.html"
        empty.write_text(built_page(rubric, all_met), encoding="utf-8")
        if why := measured(browser, empty.as_uri(), rubric, all_met)["empty fixes"]:
            failures.setdefault("empty fixes", why)
        browser.close()
    print(f"ok {len(found)}")
    for fact in (*frame.FACTS, *PAGE_FACTS):
        if fact not in failures:
            print(f"{fact} ok")
    print("Each line ending in ok names a fact the browser measured on every page, and `empty fixes` on the last one rebuilt with every criterion met.")
    print("Every page fits 390 and 1200 px in light and dark and cuts no text.")
    if failures:
        raise Refused("; ".join(f"{fact}: {why}" for fact, why in failures.items()))


def main(args):
    try:
        if len(args) in (2, 3) and args[0] == "--check":
            check(*args[1:])
        elif len(args) == 3 and not any(argument.startswith("-") for argument in args):
            pathlib.Path(args[2]).write_text(built_page(*load(args[0], args[1])), encoding="utf-8")
            print(f"wrote {args[2]}")
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except (Refused, OSError, ValueError) as e:
        print(f"refused: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

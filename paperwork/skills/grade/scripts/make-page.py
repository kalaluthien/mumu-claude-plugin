#!/usr/bin/env python3
"""Build the HTML report card of one target from its spec and its grades file.

usage: make-page.py SPEC.json GRADES.json OUT.html   one self-contained page; refused when the grades break the grammar
                                                       or the spec
       make-page.py verdicts SPEC.json GRADES.json   print the verdict file the grades make, for score-spec.py
       make-page.py --check DIR                      build every DIR/X/ that holds spec.json and grades.json, check the
                                                       page in headless Chromium and print "ok N"; a kept DIR/X/report.html
                                                       must equal the page built
       make-page.py --layout DIR                     measure every DIR/X/'s page at 390 and 1200 px, light and dark,
                                                       and print "layout ok N"
       make-page.py --capture PAGE.html DIR          write four PNGs of a built page: 1200 and 390 px, light and dark
                                                       (every call with -- needs playwright: uv run --with playwright==1.64.1
                                                       python3 make-page.py ...)

Exit status 0 means done, 1 a refusal, 2 a usage error.
"""
import html
import json
import pathlib
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))

from rubric.grades import failed, judged, problems, verdicts  # noqa: E402
from rubric.model import tier_scores  # noqa: E402
from rubric.spec import violations  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "page.html"
SCORE_SPEC = HERE / "score-spec.py"
WIDTHS = (390, 1200)
URL = re.compile(r"https?://\S+")


class Refused(Exception):
    pass


def load(spec_path, grades_path):
    """The spec and the grades, or Refused naming the first rule they break."""
    spec_bytes = pathlib.Path(spec_path).read_bytes()
    try:
        spec, grades = json.loads(spec_bytes), json.loads(pathlib.Path(grades_path).read_text(encoding="utf-8"))
    except ValueError as e:
        raise Refused(f"not a JSON document: {e}")
    if errors := [f"{where}: {message}" for rule, where, message, severity in violations(spec) if severity == "error"]:
        raise Refused(f"{spec_path}: {errors[0]}")
    if any(tier.get("pairwise") for tier in spec["tiers"]):
        raise Refused(f"{spec_path}: a report grades one target, so its spec takes no pairwise tier")
    if wrong := problems(spec, spec_bytes, grades):
        raise Refused(f"{grades_path}: {wrong[0]}")
    return spec, grades


def escape(text):
    return html.escape(str(text))


def linked(text):
    """Escaped text whose urls are links."""
    out, last = [], 0
    for match in URL.finditer(text):
        url = match.group().rstrip(".,;)")
        out += [escape(text[last:match.start()]), f'<a href="{escape(url)}">{escape(url)}</a>']
        last = match.start() + len(url)
    return "".join(out + [escape(text[last:])])


def status_word(criterion, grade):
    if not judged(grade):
        return "? Not judged"
    if criterion["polarity"] == "+":
        return ("✓ Met", "✗ Not met")[failed(criterion, grade)]
    return ("✓ No error", "✗ Error found")[failed(criterion, grade)]


def fix_list(spec, grades):
    """(tier, criterion, grade) of each failed criterion, highest tier first, in the spec's order within a tier."""
    return [(tier, criterion, grades["grades"][criterion["id"]]) for tier in spec["tiers"] for criterion in tier["criteria"]
            if failed(criterion, grades["grades"][criterion["id"]])]


def verdict_sentence(spec, grades, scores):
    for tier, score in zip(spec["tiers"], scores):
        if score < 1:
            missed = sum(failed(criterion, grades["grades"][criterion["id"]]) for criterion in tier["criteria"])
            unknown = sum(not judged(grades["grades"][criterion["id"]]) for criterion in tier["criteria"])
            return (f"Falls short at “{tier['name']}”: {missed} of {len(tier['criteria'])} criteria "
                    f"{'fails' if missed == 1 else 'fail'} there"
                    + (f", and {unknown} could not be judged." if unknown else "."))
    return "Meets every criterion of the rubric."


def tier_rows(spec, grades, scores):
    rows = []
    for tier, score in zip(spec["tiers"], scores):
        criteria = tier["criteria"]
        given = [grades["grades"][criterion["id"]] for criterion in criteria]
        met = sum(judged(grade) and not failed(criterion, grade) for criterion, grade in zip(criteria, given))
        unknown = sum(not judged(grade) for grade in given)
        target = tier.get("pass", 1) if tier.get("mask_below") else 1
        masked = score == 0 and met > 0
        count = (f"{met} of {len(criteria) - unknown} judged met" + (f", {unknown} not judged" if unknown else "")
                 + (" · zeroed by a higher tier's mask" if masked else ""))
        rows.append(f'<div class="tier-name">{escape(tier["name"])}</div>'
                    f'<div class="bullet" role="img" aria-label="{escape(count)}"><div class="fill" style="width:{score * 100:.1f}%"></div>'
                    f'<div class="target" style="left:calc({target * 100:.1f}% - 1px)"></div></div>'
                    f'<div class="tier-count" data-tier="{escape(tier["id"])}" data-score="{score:.3g}">{escape(count)}</div>')
    return "".join(rows)


def card(tier, criterion, grade):
    bad = failed(criterion, grade)
    runs = grade.get("runs", [])
    split = (f'<span class="split">the {len(runs)} judge runs split; the stricter verdict is kept</span>'
             if len(set(runs)) > 1 else "")
    where = f'<div class="where">{linked(grade["where"])}</div>' if grade.get("where") else ""
    fix = f'<p class="fix"><b>Fix:</b> {linked(grade["fix"])}</p>' if bad and grade.get("fix") else ""
    state = "unjudged" if not judged(grade) else "failed" if bad else "passed"
    return (f'<article class="crit {state}" id="c-{escape(criterion["id"])}" '
            f'data-criterion="{escape(criterion["id"])}">'
            f'<div class="crit-head"><span class="status">{status_word(criterion, grade)}</span>'
            f'<span class="crit-text">{linked(criterion["text"])}</span>{split}'
            f'<span class="crit-id">{escape(criterion["id"])}</span></div>'
            f'<details{" open" if bad or not judged(grade) else ""}><summary>Evidence</summary>'
            f'<blockquote class="evidence">{linked(grade["evidence"])}</blockquote>{where}'
            f'<p class="why">{linked(grade["why"])}</p></details>{fix}</article>')


def body(spec, grades):
    target, subject, judge = grades["target"], grades["subject"], grades["judge"]
    scores = tier_scores(spec, verdicts(spec, grades), target["name"])
    fixes = fix_list(spec, grades)
    out = [f'<div class="eyebrow">Report card</div><h1>{escape(target["name"])}</h1>',
           f'<p class="lede">{escape(subject["kind"])}</p>',
           f'<div class="meta"><span>{linked(target["where"])}</span><span>version {escape(target["version"])}</span>'
           f'<span>judge {escape(judge["model"])}, {judge["runs"]} run{"s" if judge["runs"] > 1 else ""}</span>'
           f'<span>spec {escape(grades["spec_sha"])}</span></div>',
           f'<section class="verdict" id="verdict"><p>{escape(verdict_sentence(spec, grades, scores))}</p>'
           f'<div class="tiers">{tier_rows(spec, grades, scores)}</div>'
           '<p class="legend">Tiers run highest first and never trade off: a lower tier only orders what the higher '
           'ones tie. Each bar is the share of its tier met; the mark is the share the tier asks for.</p></section>',
           '<h2>Fix first</h2>']
    if fixes:
        items = "".join(f'<li data-fix="{escape(failed_grade["fix"])}"><span class="fix-tier">{escape(failed_tier["name"])}</span>'
                        f'<a href="#c-{escape(failed_criterion["id"])}">{linked(failed_grade["fix"])}</a></li>' for failed_tier, failed_criterion, failed_grade in fixes)
        out.append(f'<ol class="fixes">{items}</ol><button class="copy" id="copy-fixes" type="button">Copy the fix list</button>')
    else:
        out.append('<p class="none">Nothing to fix: every criterion is met.</p>')
    out.append('<h2>Criteria</h2>')
    for tier in spec["tiers"]:
        criteria = sorted((criterion for criterion in tier["criteria"] if judged(grades["grades"][criterion["id"]])),
                          key=lambda criterion: not failed(criterion, grades["grades"][criterion["id"]]))
        out.append(f'<h3>{escape(tier["name"])}</h3>' + "".join(card(tier, criterion, grades["grades"][criterion["id"]]) for criterion in criteria))
    unjudged = [(unjudged_tier, unjudged_criterion) for unjudged_tier in spec["tiers"] for unjudged_criterion in unjudged_tier["criteria"] if not judged(grades["grades"][unjudged_criterion["id"]])]
    if unjudged:
        out.append('<h2>Not judged</h2><p class="none">These could not be checked, each for the reason on its card. '
                   'They are left out of the counts above, but the tier score treats each as failed, so the order never '
                   'rewards what nobody checked.</p>' + "".join(card(unjudged_tier, unjudged_criterion, grades["grades"][unjudged_criterion["id"]]) for unjudged_tier, unjudged_criterion in unjudged))
    frameworks = "".join(f"<li>{linked(framework)}</li>" for framework in subject["frameworks"])
    out.append('<h2>What was graded</h2><dl class="subject">'
               f'<dt>Kind</dt><dd>{escape(subject["kind"])}</dd><dt>Purpose</dt><dd>{linked(subject["purpose"])}</dd>'
               f'<dt>Reader</dt><dd>{linked(subject["reader"])}</dd><dt>Criteria drawn from</dt><dd><ul>{frameworks}</ul></dd>'
               f'<dt>Rubric</dt><dd>{linked(spec["task"]["instruction"])}</dd></dl>')
    estimated = spec["judge"].get("calibration", {}).get("estimated", True)
    out.append('<footer><p>Each criterion is one yes-or-no check. '
               f'{escape(judge["model"])} graded every criterion in {judge["runs"]} fresh '
               f'run{"s" if judge["runs"] > 1 else ""} that saw only the target and the rubric, quoting its evidence before '
               'each verdict; when runs split, the stricter verdict counts.</p>'
               f'<p>The judge’s error rate per tier is {"estimated, not measured on human labels" if estimated else "measured on human labels"}. '
               'Read the tier counts as an order between versions of a target, not as a percentage of quality.</p></footer>')
    return "\n".join(out)


def build(spec_path, grades_path):
    spec, grades = load(spec_path, grades_path)
    page = TEMPLATE.read_text(encoding="utf-8")
    return page.replace("__TITLE__", escape(f"Report card: {grades['target']['name']}")).replace("__BODY__", body(spec, grades))


def examples(folder):
    found = sorted(path for path in pathlib.Path(folder).iterdir() if (path / "spec.json").is_file() and (path / "grades.json").is_file())
    if not found:
        raise Refused(f"{folder}: no folder holds spec.json and grades.json")
    return found


def score_spec_scores(spec_path, verdicts_file):
    """Each tier's score as score-spec.py order prints it, so the page is checked against the scoring script."""
    out = subprocess.run([sys.executable, str(SCORE_SPEC), "order", str(spec_path), str(verdicts_file)],
                         capture_output=True, text=True, check=True).stdout.splitlines()[0]
    return dict(pair.split(" ") for pair in re.search(r"\(([^()]*)\)$", out).group(1).split(", "))


def check_one(page, folder, temporary_folder):
    spec, grades = load(folder / "spec.json", folder / "grades.json")
    out = pathlib.Path(temporary_folder) / f"{folder.name}.html"
    out.write_text(build(folder / "spec.json", folder / "grades.json"), encoding="utf-8")
    kept = folder / "report.html"
    if kept.is_file() and kept.read_text(encoding="utf-8") != out.read_text(encoding="utf-8"):
        raise Refused(f"{folder}: report.html differs from the page its spec and grades build; rebuild it")
    verdict_file = pathlib.Path(temporary_folder) / f"{folder.name}.verdicts.json"
    verdict_file.write_text(json.dumps(verdicts(spec, grades)), encoding="utf-8")
    want = score_spec_scores(folder / "spec.json", verdict_file)
    leaks = []
    page.on("request", lambda request: leaks.append(request.url) if not request.url.startswith(("file:", "data:")) else None)
    page.goto(out.as_uri())
    shown = dict(page.eval_on_selector_all(".tier-count", "els => els.map(e => [e.dataset.tier, e.dataset.score])"))
    if shown != want:
        raise Refused(f"{folder}: tier scores shown {shown}, score-spec.py computes {want}")
    cards = page.eval_on_selector_all(".crit", "els => els.map(e => [e.dataset.criterion, e.querySelector('.status').innerText, "
                                      "e.querySelector('.evidence').textContent.trim()])")
    ids = [criterion["id"] for tier in spec["tiers"] for criterion in tier["criteria"]]
    if sorted(card_row[0] for card_row in cards) != sorted(ids):
        raise Refused(f"{folder}: the page shows criteria {sorted(card_row[0] for card_row in cards)}, the spec has {sorted(ids)}")
    if bare := [card_row[0] for card_row in cards if not card_row[1].strip() or not card_row[2]]:
        raise Refused(f"{folder}: no verdict or no evidence shown for {', '.join(bare)}")
    listed = page.eval_on_selector_all("ol.fixes li a", "els => els.map(e => e.getAttribute('href').slice(3))")
    expected = [criterion["id"] for _, criterion, _ in fix_list(spec, grades)]
    if listed != expected:
        raise Refused(f"{folder}: fixes listed {listed}, highest tier first they are {expected}")
    if leaks:
        raise Refused(f"{folder}: requests left for {', '.join(leaks)}")


def check(folder):
    from playwright.sync_api import sync_playwright
    found = examples(folder)
    with tempfile.TemporaryDirectory() as temporary_folder, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for example in found:
            page = browser.new_page()
            check_one(page, example, temporary_folder)
            page.close()
        browser.close()
    print(f"ok {len(found)}")
    print("Each page shows the tier scores score-spec.py computes, every criterion with its verdict and evidence, the "
          "failed ones as fixes highest tier first, and sends no request off the file.")


def layout(folder):
    from playwright.sync_api import sync_playwright
    found = examples(folder)
    with tempfile.TemporaryDirectory() as temporary_folder, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for example in found:
            out = pathlib.Path(temporary_folder) / f"{example.name}.html"
            out.write_text(build(example / "spec.json", example / "grades.json"), encoding="utf-8")
            for width in WIDTHS:
                for scheme in ("light", "dark"):
                    page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=scheme)
                    page.goto(out.as_uri())
                    wide = page.evaluate("document.documentElement.scrollWidth")
                    if wide > width:
                        raise Refused(f"{example}: {wide} px wide at {width} px, {scheme}")
                    words = page.eval_on_selector_all(".status", "els => els.map(e => e.innerText.trim())")
                    if not words or any(not re.search(r"[A-Za-z]{2}", word) for word in words):
                        raise Refused(f"{example}: a verdict shows no word at {width} px, {scheme}")
                    clipped = page.eval_on_selector_all(
                        ".crit-text, .tier-name, .tier-count, h1",
                        "els => els.filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.innerText.slice(0, 30))")
                    if clipped:
                        raise Refused(f"{example}: text cut at {width} px, {scheme}: {clipped[0]}")
                    page.close()
        browser.close()
    print(f"layout ok {len(found)}")
    print("Every page fits 390 and 1200 px in light and dark, cuts no text, and names each verdict in words.")


def capture(page_path, folder):
    from playwright.sync_api import sync_playwright
    folder = pathlib.Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for width in WIDTHS:
            for scheme in ("light", "dark"):
                page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=scheme)
                page.goto(pathlib.Path(page_path).resolve().as_uri())
                page.screenshot(path=str(folder / f"{width}-{scheme}.png"), full_page=True)
                page.close()
        browser.close()
    print(f"wrote 4 PNGs into {folder}")


def main(args):
    try:
        if len(args) == 2 and args[0] == "--check":
            check(args[1])
        elif len(args) == 2 and args[0] == "--layout":
            layout(args[1])
        elif len(args) == 3 and args[0] == "--capture":
            capture(args[1], args[2])
        elif len(args) == 3 and args[0] == "verdicts":
            spec, grades = load(args[1], args[2])
            print(json.dumps(verdicts(spec, grades), indent=1))
        elif len(args) == 3 and not any(argument.startswith("-") for argument in args):
            pathlib.Path(args[2]).write_text(build(args[0], args[1]), encoding="utf-8")
            print(f"wrote {args[2]}")
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except (Refused, OSError) as e:
        print(f"refused: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

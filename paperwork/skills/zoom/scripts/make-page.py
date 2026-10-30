#!/usr/bin/env python3
"""Build the clickable HTML page of one Schema document; it runs no proof.

usage: make-page.py DOC.json [PROOFS.json] OUT.html
                                            one self-contained page, with the verdicts prove-schema.py --proofs wrote;
                                              refused when the document breaks the grammar, a chart has a name it cannot
                                              place, a scenario leaves the edges or the proofs are of another document
       make-page.py --check DIR             build every DIR/X/schema.json, with DIR/X/proofs.json if there, check the page in headless Chromium and print
                                              "ok N", then "<fact> ok" for each fact it measured on every page; a kept
                                              DIR/X/page.html must equal the page built
       make-page.py --layout DIR            measure every level of every DIR/X/'s page at 390 and 1200 px, light and
                                              dark, and print "layout ok N"
       make-page.py --capture PAGE.html DIR write the page's screens as numbered PNGs at 1200 px
                                              (every call with -- needs playwright: uv run --with playwright==1.64.1
                                              python3 make-page.py ...)

Exit status 0 means done, 1 a refusal, 2 a usage error.
"""
import collections
import html
import json
import pathlib
import re
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))

from page import frame  # noqa: E402
from schema.model import Model, edge_across_levels, references, shape  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "page.html"
WIDTHS = (390, 1200)
PANEL_STATE = "document.querySelector('.detail:not([hidden])') === null"
PANEL_CHANGE = "document.querySelector('.level:not(.away) .node').dispatchEvent(new MouseEvent('click', {bubbles: true}))"
GROUPS = (("scenarios", "Scenarios", "Scenario"), ("rules", "Rules", "Rule"))
WHY = {"scenarios": "Each one walks the chart step by step.", "rules": "Each one marks what it concerns, and a counterexample plays its run."}
VERDICTS = {"pass": "✓", "counterexample": "✗", "unproved": "?"}
RESPONSE_PATHS = ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "<form", "<input", "<textarea", "<select")
HINTS = ("✓ A rule passes", "✗ A run breaks it", "Press a box or a line to read it and its source")
LEGEND = {
    "state": ('<rect x="1" y="1" width="26" height="14" rx="5"/>', "State: where a thing is now"),
    "part": ('<rect x="1" y="1" width="26" height="14" rx="1"/>', "Part: a piece of the system"),
    "transition": ('<line x1="1" y1="8" x2="27" y2="8"/>', "Transition: a move between states"),
    "call": ('<line x1="1" y1="8" x2="27" y2="8" stroke-dasharray="5 4"/>', "Call: one part uses another"),
}


class Refused(Exception):
    pass


def unplaced(model):
    """What a chart cannot draw, each a sentence, since the page runs no other structure check."""
    named = [node["id"] for level in model.levels.values() for node in level["nodes"]]
    out = references(model) + edge_across_levels(model) + [f"{node_id} names two nodes" for node_id in named if named.count(node_id) > 1]
    for level_id, level in model.levels.items():
        initial, here = level.get("initial", []), {node["id"] for node in level["nodes"]}
        out += [f"{level_id}: {start} starts no node of this level" for start in ([initial] if isinstance(initial, str) else initial) if start not in here]
    return out


def load(path):
    """The document's model, or Refused naming the first thing that stops the page."""
    try:
        document = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except ValueError as e:
        raise Refused(f"not a JSON document: {e}")
    if wrong := shape(document):
        raise Refused(f"{path}: {wrong[0][1]}")
    model = Model(document)
    if wrong := unplaced(model):
        raise Refused(f"{path}: {wrong[0]}")
    for scenario in document["scenarios"]:
        if wrong := model.walk(scenario)[1]:
            raise Refused(f"{path}: {wrong[0]}")
    return model


def read_proofs(path, model):
    """Each rule's proof by slug, or Refused when the file does not fit this document, since a page must not show a
    verdict on what it no longer draws."""
    try:
        rules = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))["rules"]
        named = [(rule["slug"], rule["verdict"], rule["nodes"], rule.get("steps", [])) for rule in rules]
        drawn = [(slug, name, name in model.nodes) for slug, _, nodes, steps in named for name in nodes + [node for step in steps for node in step["nodes"]]]
        drawn += [(slug, key, key in model.edges) for slug, _, _, steps in named for step in steps for key in step["edges"]]
    except (ValueError, KeyError, TypeError) as e:
        raise Refused(f"{path}: not a proofs file: {e!r}")
    slugs = {rule["slug"] for rule in model.document["rules"]}
    for slug, verdict, *_ in named:
        if slug not in slugs:
            raise Refused(f"{path}: names rule {slug}, which the document lacks")
        if verdict not in VERDICTS:
            raise Refused(f"{path}: {slug} has no verdict {verdict}")
    if lost := next((f"{slug}: {name}" for slug, name, known in drawn if not known), None):
        raise Refused(f"{path}: {lost} is in no chart of the document")
    return {rule["slug"]: rule for rule in rules}


def escape(text):
    return html.escape(str(text))


def outline(level, nodes, edges):
    """What the copy icon puts on the clipboard for a level: its words, without the drawing."""
    label = {node["id"]: node["label"] for node in nodes}
    return "\n".join([level["title"], level["why"], ""] + [f'- {node["label"]}: {node["meta"]["description"]} ({node["meta"]["source"]})' for node in nodes]
                     + [f'- {label[edge["from"]]} → {label[edge["to"]]}, {edge["label"]}: {edge["meta"]["description"]}' for edge in edges])


def level_data(model, level_id):
    level, states = model.levels[level_id], model.states(level_id)
    initial = level.get("initial", [])
    nodes = [{"id": node["id"], "label": node["label"], "state": node["id"] in states, "lane": node.get("region") or node.get("area"),
              "opens": node["id"] if "opens" in node else None, "attrs": node.get("attrs", []), "rules": node.get("rules", []), "meta": node["meta"]}
             for node in level["nodes"]]
    edges = [{"key": key, "from": edge["from"], "to": edge["to"], "kind": edge["kind"], "label": edge["label"], "changes": edge.get("changes", []),
              "rules": edge.get("rules", []), "meta": edge["meta"]} for key, (edge_level, edge) in model.edges.items() if edge_level == level_id]
    return {"id": level_id, "title": level["title"], "initial": [initial] if isinstance(initial, str) else initial,
            "lanes": level.get("regions", []) + level.get("areas", []), "nodes": nodes, "edges": edges, "copy": outline(level, level["nodes"], level["edges"])}


def words(slug):
    return slug.replace("-", " ")


def step_level(model, step, previous):
    """The level a step plays on: where most of it happens, the one shown already on a tie, so the chart jumps least."""
    counts = collections.Counter([model.node_level[node] for node in step["nodes"]] + [model.edges[key][0] for key in step["edges"]])
    return max(counts or [previous or "root"], key=lambda level_id: (counts[level_id], level_id == previous))


def scenario_item(model, scenario):
    steps, level_id = [], None
    for told, step in zip(scenario["walk"], model.walk(scenario)[0]):
        level_id = step_level(model, step, level_id)
        steps.append({**step, "level": level_id, "does": told["does"], "expects": told["expects"]})
    return {"key": f'scenario-{scenario["slug"]}', "kind": "Scenario", "title": words(scenario["slug"]), "text": scenario["text"], "nodes": [], "steps": steps}


def run_text(model, step):
    """What a step of a counterexample does, from the only words a proof has: the labels it names."""
    label = lambda node_id: model.nodes[node_id]["label"]
    moves = [f'{label(edge["from"])} goes to {label(edge["to"])} by {edge["label"]}.' for key, (_, edge) in model.edges.items() if key in step["edges"]]
    return ("At the same time:\n" if len(moves) > 1 else "") + "\n".join(moves) or f'Together these break it: {", ".join(label(node) for node in step["nodes"])}.'


def rule_item(model, rule, proof):
    nodes, steps, level_id = proof["nodes"] if proof else model.concerns(rule["slug"]), [], None
    for index, step in enumerate(proof.get("steps", []) if proof else []):
        level_id = step_level(model, step, level_id)
        steps.append({**step, "level": level_id, "does": run_text(model, step), "expects": "By here this run has broken the rule." if index == len(proof["steps"]) - 1 else ""})
    home = collections.Counter(model.node_level[node] for node in nodes).most_common(1)
    return {"key": f'rule-{rule["slug"]}', "kind": "Rule", "title": words(rule["slug"]), "text": rule["meta"]["description"], "strength": rule["kind"],
            "verdict": proof["verdict"] if proof else None, "why": proof.get("why", "") if proof else "", "source": rule["meta"]["source"], "nodes": nodes,
            "names": [model.nodes[node]["label"] for node in nodes], "level": home[0][0] if home else "root", "steps": steps}


def page_data(model, proofs):
    return {"levels": [level_data(model, level_id) for level_id in model.levels],
            "rules": {rule["slug"]: {"kind": rule["kind"], **rule["meta"]} for rule in model.document["rules"]},
            "items": [scenario_item(model, scenario) for scenario in model.document["scenarios"]] + [rule_item(model, rule, proofs.get(rule["slug"])) for rule in model.document["rules"]]}


def trail(model, level_id):
    """The links from the root to this level, so a reader always sees where they are and can go back."""
    chain, opener = [], model.parent[level_id]
    while opener:
        chain.insert(0, model.node_level[opener])
        opener = model.parent[chain[0]]
    return " <span aria-hidden=\"true\">›</span> ".join(f'<a href="#level-{escape(step)}">{escape(model.levels[step]["title"])}</a>' for step in chain)


def inside(model):
    """What the root's chart only opens, so the first screen names the whole system."""
    rows = "".join(f'<li><a href="#level-{escape(level_id)}">{escape(level["title"])}</a>: {escape(", ".join(node["label"] for node in level["nodes"]))}</li>'
                   for level_id, level in model.levels.items() if level_id != "root")
    return f'<h2>Main parts</h2>\n<ul class="inside" aria-label="What is inside">{rows}</ul>' if rows else ""


def legend(model):
    """Every kind the document uses, so a level of one kind still says how the other reads."""
    kinds = [kind for kind in LEGEND if kind in {"state" if node_id in model.states(model.node_level[node_id]) else "part" for node_id in model.nodes} | {edge["kind"] for _, edge in model.edges.values()}]
    return '<ul class="legend" aria-label="What the shapes mean">' + "".join(
        f'<li class="key-{kind}"><svg viewBox="0 0 28 16" width="28" height="16" aria-hidden="true">{LEGEND[kind][0]}</svg>{escape(LEGEND[kind][1])}</li>' for kind in kinds) + "".join(f"<li>{hint}</li>" for hint in HINTS) + "</ul>"


def section(model, level_id):
    level = model.levels[level_id]
    crumbs = trail(model, level_id) or escape(model.document["title"])
    return (f'<section class="view level" id="level-{escape(level_id)}">\n<p class="crumbs">{crumbs}</p>\n<h1>{escape(level["title"])}</h1>\n'
            f'<p class="lede">{escape(level["why"])}</p>\n<div class="chart" data-level="{escape(level_id)}"></div>\n{legend(model)}\n{inside(model) if level_id == "root" else ""}\n'
            '<div class="detail" hidden></div>\n</section>')


TONES = {"pass": "pass", "counterexample": "fail", "unproved": "warn"}


def badge(verdict):
    return f'<span class="frame-tag verdict {TONES[verdict]}" data-verdict="{verdict}">{verdict.capitalize()}</span>' if verdict else ""


def overview(target, title, why, items):
    rows = "".join(f'<li><a href="#{item["key"]}">{escape(item["title"])}</a> {badge(item.get("verdict"))}<p>{escape(item["text"])}</p></li>' for item in items)
    return f'<section class="view overview away" id="{target}">\n<h1>{title}</h1>\n<p class="lede">{why}</p>\n<ul class="items">{rows}</ul>\n</section>'


def navigation(model, items):
    rest = [(f"level-{level_id}", model.levels[level_id]["title"]) for level_id in model.levels if level_id != "root"]
    levels = ("level-root", model.levels["root"]["title"], rest) if rest else ("level-root", model.levels["root"]["title"])
    label = lambda item: f'{VERDICTS[item["verdict"]]} {item["title"]}' if item.get("verdict") else item["title"]
    groups = [(target, name, [(item["key"], label(item)) for item in items if item["kind"] == kind]) for target, name, kind in GROUPS]
    return [levels, *(group for group in groups if group[2])]


def build(path, proofs_path=None):
    model = load(path)
    data = page_data(model, read_proofs(proofs_path, model) if proofs_path else {})
    items = data["items"]
    views = [overview(target, name, WHY[target], [item for item in items if item["kind"] == kind]) for target, name, kind in GROUPS if any(item["kind"] == kind for item in items)]
    views += [f'<section class="view item away" id="{item["key"]}"><div class="bar"></div></section>' for item in items]
    sections = "\n".join(views + [section(model, level_id) for level_id in model.levels])
    # a `<` could close or hide its script
    embedded = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    # one pass, so no text of the document is read as a placeholder
    fills = {"__SECTIONS__": sections, "__DATA__": embedded}
    content = re.sub("|".join(fills), lambda found: fills[found.group()], TEMPLATE.read_text(encoding="utf-8"))
    return frame.build(model.document["title"], content, navigation(model, items))


def examples(folder):
    found = sorted(path for path in pathlib.Path(folder).iterdir() if (path / "schema.json").is_file())
    if not found:
        raise Refused(f"{folder}: no folder holds schema.json")
    return found


def proofs_of(example):
    return example / "proofs.json" if (example / "proofs.json").is_file() else None


def example_data(example):
    model = load(example / "schema.json")
    return model, page_data(model, read_proofs(proofs_of(example), model) if proofs_of(example) else {})


def built_page(example, temporary_folder):
    out = pathlib.Path(temporary_folder) / f"{example.name}.html"
    out.write_text(build(example / "schema.json", proofs_of(example)), encoding="utf-8")
    kept = example / "page.html"
    if kept.is_file() and kept.read_text(encoding="utf-8") != out.read_text(encoding="utf-8"):
        raise Refused(f"{example}: page.html differs from the page its schema builds; rebuild it")
    return out


def open_level(page, level_id):
    page.evaluate("id => { location.hash = id; }", f"level-{level_id}")
    page.wait_for_function("id => !document.getElementById(id).classList.contains('away')", arg=f"level-{level_id}")


def chart(page, data):
    styles = {}
    for level in data["levels"]:
        open_level(page, level["id"])
        drawn = page.evaluate("""id => {
          const section = document.getElementById(id);
          const boxes = [...section.querySelectorAll('.node .shape')].map(shape => shape.getBoundingClientRect());
          const apart = (a, b) => a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top;
          return {nodes: boxes.length, edges: section.querySelectorAll('.edge .line').length,
                  overlap: boxes.some((a, i) => boxes.slice(i + 1).some(b => !apart(a, b))),
                  styles: [...section.querySelectorAll('.edge:not(.edge-tag)')].map(edge => [edge.dataset.kind, getComputedStyle(edge.querySelector('.line')).strokeDasharray])};
        }""", f'level-{level["id"]}')
        if drawn["nodes"] != len(level["nodes"]) or drawn["edges"] != len(level["edges"]):
            return f'{level["id"]} draws {drawn["nodes"]} nodes and {drawn["edges"]} edges of {len(level["nodes"])} and {len(level["edges"])}'
        if drawn["overlap"]:
            return f'{level["id"]} draws two nodes over each other'
        for kind, dash in drawn["styles"]:
            styles.setdefault(kind, set()).add(dash)
    if len(styles.get("call", set()) | styles.get("transition", set())) != len(styles.get("call", set())) + len(styles.get("transition", set())):
        return "a call and a transition share a line style"
    return None


def detail_panel(page, data):
    for level in data["levels"]:
        open_level(page, level["id"])
        shown = page.locator(f'#level-{level["id"]} .detail')
        pairs = [(f'.node[data-id="{node["id"]}"] text', node) for node in level["nodes"]] + [(f'.edge[data-key="{edge["key"]}"] .edge-label', edge) for edge in level["edges"]]
        for selector, element in pairs:
            page.locator(f'#level-{level["id"]} {selector}').first.click()
            text = shown.inner_text() if shown.is_visible() else ""
            if element["meta"]["description"] not in text or element["meta"]["source"] not in text:
                return f'{element.get("id", element.get("key"))} shows no description and source'
    return None


def level_opens(page, data):
    listed = page.eval_on_selector_all(".frame-nav a", "links => links.map(link => link.getAttribute('href'))")
    if missing := [level["id"] for level in data["levels"] if f'#level-{level["id"]}' not in listed]:
        return f"the navigation lacks {missing[0]}"
    for level in data["levels"]:
        for node in level["nodes"]:
            if node["opens"]:
                open_level(page, level["id"])
                page.locator(f'#level-{level["id"]} a.opener[href="#level-{node["opens"]}"]').click()
                if page.locator(f'#level-{node["opens"]}').evaluate("section => section.classList.contains('away')"):
                    return f'{node["id"]} does not open its level in one action'
    return None


def read_only(page, _):
    if count := page.evaluate("document.querySelectorAll('form, input, textarea, select, [contenteditable]').length"):
        return f"{count} elements take text or an answer"
    if found := [word for word in RESPONSE_PATHS if word in page.content()]:
        return f"the page holds a response path: {found[0]}"
    return None


def text_as_written(page, data):
    for level in data["levels"]:
        open_level(page, level["id"])
        if page.locator(f'#level-{level["id"]} .lede').inner_text() not in level["copy"]:
            return f'{level["id"]} shows a text other than the one written'
    return None


def open_item(page, key):
    page.evaluate("id => { location.hash = id; }", key)
    page.wait_for_function("id => !document.getElementById(id).classList.contains('away')", arg=key)


def marked(page, selector):
    return page.evaluate("selector => document.querySelector('.level:not(.away)').querySelectorAll(selector).length", selector)


def navigation_items(page, data):
    listed = page.eval_on_selector_all(".frame-nav a", "links => links.map(link => link.getAttribute('href').slice(1))")
    wanted = [f'level-{level["id"]}' for level in data["levels"]] + [item["key"] for item in data["items"]]
    if missing := [key for key in wanted if key not in listed]:
        return f"the navigation lacks {missing[0]}"
    if extra := [key for key in listed if key not in wanted and key not in (target for target, *_ in GROUPS)]:
        return f"the navigation also lists {extra[0]}"
    for item in data["items"]:
        page.locator(f'.frame-nav a[href="#{item["key"]}"]').click()
        if page.locator(f'#{item["key"]} .bar').is_hidden() or marked(page, ".path, .now, .related") == 0 and (item["steps"] or item["nodes"]):
            return f'{item["key"]} draws nothing on the chart'
    return None


def played(page, item):
    """Walk an item's steps forward and back on the bar, or say what went wrong."""
    open_item(page, item["key"])
    bar = page.locator(f'#{item["key"]} .bar')
    for index, step in enumerate(item["steps"]):
        count, text = bar.locator(".bar-count").inner_text(), bar.locator(".bar-step").inner_text()
        if count != f'Step {index + 1} of {len(item["steps"])}':
            return f'{item["key"]} shows {count} at step {index + 1}'
        if step["does"] not in text or step["expects"] not in text:
            return f'{item["key"]} step {index + 1} lacks its text'
        if not page.locator(f'#level-{step["level"]}').is_visible():
            return f'{item["key"]} step {index + 1} leaves {step["level"]}'
        if marked(page, ".now") == 0:
            return f'{item["key"]} step {index + 1} marks nothing'
        breaks = item.get("verdict") == "counterexample" and index == len(item["steps"]) - 1
        if page.locator(f'#level-{step["level"]} .step-tag text').first.text_content() != f"Step {index + 1}" + (": broken" if breaks else "") or bar.locator('.bar-chip[aria-current="step"]').inner_text() != str(index + 1):
            return f'{item["key"]} step {index + 1} names another step'
        if item.get("verdict") and step["does"] not in bar.locator('.bar-run [aria-current="step"]').inner_text():
            return f'{item["key"]} step {index + 1} marks another line of its run'
        if index + 1 < len(item["steps"]):
            bar.locator(".bar-next").click()
    if not bar.locator(".bar-next").is_disabled():
        return f'{item["key"]} goes past its last step'
    if len(item["steps"]) > 1:
        bar.locator(".bar-previous").click()
        if bar.locator(".bar-count").inner_text() != f'Step {len(item["steps"]) - 1} of {len(item["steps"])}':
            return f'{item["key"]} does not step back'
        bar.locator(".bar-chip").first.click()
        if bar.locator(".bar-count").inner_text() != f'Step 1 of {len(item["steps"])}':
            return f'{item["key"]} does not go to a picked step'
    return None


def scenario_playback(page, data):
    return next((why for item in data["items"] if item["kind"] == "Scenario" and (why := played(page, item))), None)


def status_tags(page, data):
    rules = [item for item in data["items"] if item["kind"] == "Rule"]
    return f"{page.locator('.frame-tag.verdict').count()} tags for {len(rules)} rules" if page.locator(".frame-tag.verdict").count() < len(rules) else None


def verdict_badge(page, data):
    for item in data["items"]:
        if item["kind"] == "Rule":
            open_item(page, item["key"])
            shown = page.locator(f'#{item["key"]} .verdict')
            if ((shown.inner_text().lower(), shown.get_attribute("data-verdict")) if shown.count() else (None, None)) != (item["verdict"], item["verdict"]):
                return f'{item["key"]} shows no {item["verdict"]} badge'
            if item["nodes"] and marked(page, ".related, .now") == 0:
                return f'{item["key"]} marks none of its nodes'
    return None


def counterexample_playback(page, data):
    return next((why for item in data["items"] if item.get("verdict") == "counterexample" and (why := played(page, item))), None)


def reset_from_playback(page, data):
    for item in data["items"]:
        open_item(page, item["key"])
        page.locator("#frame-reset").click()
        if not page.locator("#level-root").is_visible() or page.locator(f'#{item["key"]}').is_visible() or marked(page, ".path, .now, .related"):
            return f'reset leaves {item["key"]} playing'
    return None


FACTS = {"chart": chart, "detail panel": detail_panel, "level opens": level_opens, "read only": read_only, "text as written": text_as_written, "navigation items": navigation_items,
         "scenario playback": scenario_playback, "verdict badge": verdict_badge, "status tags": status_tags, "counterexample playback": counterexample_playback, "reset from playback": reset_from_playback}


def check(folder):
    from playwright.sync_api import sync_playwright
    found, failures = examples(folder), {}
    with tempfile.TemporaryDirectory() as temporary_folder, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for example in found:
            built, (model, data) = built_page(example, temporary_folder), example_data(example)
            for fact, why in frame.probe(browser, built.as_uri(), copied=level_data(model, "root")["copy"], change=PANEL_CHANGE, state=PANEL_STATE).items():
                failures.setdefault(fact, f"{example}: {why}")
            for fact, measure in FACTS.items():
                page = browser.new_page(viewport={"width": frame.SCREEN_WIDTH, "height": 900})
                page.set_default_timeout(frame.TIMEOUT_MS)
                page.goto(built.as_uri())
                try:
                    why = measure(page, data)
                except Exception as e:   # a control that never answers fails its own fact and leaves the others measured
                    why = str(e).splitlines()[0]
                page.close()
                if why:
                    failures.setdefault(fact, f"{example}: {why}")
        browser.close()
    print(f"ok {len(found)}")
    print("Each page holds every level of its document and sends no request off the file.")
    for fact in [*frame.FACTS, *FACTS]:
        if fact not in failures:
            print(f"{fact} ok")
    print("Each line ending in ok names a fact the browser measured on every page.")
    if failures:
        raise Refused("; ".join(f"{fact}: {why}" for fact, why in failures.items()))


FITS = """() => {
  const section = document.querySelector('.level:not(.away)');
  const svg = section.querySelector('.chart svg');
  const frame = svg.getBoundingClientRect();
  const outside = [...svg.querySelectorAll('text')].filter(text => {
    const box = text.getBoundingClientRect();
    return box.left < frame.left - 1 || box.right > frame.right + 1 || box.top < frame.top - 1 || box.bottom > frame.bottom + 1;
  }).map(text => text.textContent);
  const clipped = [...section.querySelectorAll('h1, .crumbs, .lede, .legend li, .chart, .detail'), ...document.querySelectorAll('.item:not(.away) .bar, .item:not(.away) dd')].filter(box => box.scrollWidth > box.clientWidth + 1).map(box => box.className || box.tagName);
  const shapes = [...svg.querySelectorAll('.node')].filter(node => {
    const shape = node.querySelector('.shape').getBoundingClientRect();
    return [...node.querySelectorAll('text')].some(text => { const box = text.getBoundingClientRect(); return box.left < shape.left || box.right > shape.right; });
  }).map(node => node.dataset.id);
  const chips = [...document.querySelectorAll('.item:not(.away) .bar-chip')].filter(chip => { const words = document.createRange(); words.selectNodeContents(chip); return words.getClientRects().length > 1; }).map(chip => chip.textContent);
  const ends = [...svg.querySelectorAll('.line')].flatMap(line => [line.getPointAtLength(0), line.getPointAtLength(line.getTotalLength())]);
  const meeting = ends.filter((one, i) => ends.some((two, j) => j > i && Math.hypot(one.x - two.x, one.y - two.y) < 3)).map(() => 'two lines ending at one point');
  const along = line => Array.from({length: 121}, (_, i) => line.getPointAtLength(line.getTotalLength() * i / 120));
  const inside = (box, point, by = 0) => point.x >= box.x - by && point.x <= box.x + box.width + by && point.y >= box.y - by && point.y <= box.y + box.height + by;
  const shapeOf = id => svg.querySelector(`.node[data-id="${CSS.escape(id)}"] .shape`).getBBox();
  const adrift = [...svg.querySelectorAll('.edge-tag')].filter(pill => {
    const box = pill.querySelector('.edge-pill').getBBox(), line = svg.querySelector(`.edge:not(.edge-tag)[data-key="${CSS.escape(pill.dataset.key)}"] .line`);
    return !along(line).some(point => inside(box, point));
  }).map(pill => `label off its line: ${pill.textContent}`);
  const pills = [...svg.querySelectorAll('.edge-tag')].map(pill => ({name: pill.textContent, box: pill.querySelector('.edge-pill').getBBox()}));
  const meet = (one, two) => one.x < two.x + two.width && two.x < one.x + one.width && one.y < two.y + two.height && two.y < one.y + one.height;
  const crowded = pills.filter((one, i) => pills.some((two, j) => j > i && meet(one.box, two.box))).map(one => `labels on each other: ${one.name}`);
  const bandNames = [...svg.querySelectorAll('.band text')].filter(name => {
    const box = name.getBBox();
    return pills.some(pill => meet(pill.box, box)) || [...svg.querySelectorAll('.line')].some(line => along(line).some(point => inside(box, point)));
  }).map(name => `band name covered: ${name.textContent}`);
  const astray = levels[section.id.slice('level-'.length)].edges.filter(edge => {
    const points = along(svg.querySelector(`.edge:not(.edge-tag)[data-key="${CSS.escape(edge.key)}"] .line`)), from = shapeOf(edge.from), to = shapeOf(edge.to);
    return !inside(from, points[0], 2) || !inside(to, points.at(-1), 2) || (edge.from !== edge.to && inside(to, points.at(-4), -1));
  }).map(edge => `arrow not from ${edge.from} to ${edge.to}`);
  const stray = innerWidth <= 820 && !document.querySelector('.frame-nav.open') ? [...document.querySelectorAll('.frame-nav a')].filter(link => link.checkVisibility({visibilityProperty: true})).map(link => link.textContent) : [];
  return {wide: document.documentElement.scrollWidth, cut: [...outside, ...clipped, ...shapes, ...chips, ...meeting, ...adrift, ...crowded, ...bandNames, ...astray, ...stray]};
}"""


def layout(folder):
    from playwright.sync_api import sync_playwright
    found = examples(folder)
    with tempfile.TemporaryDirectory() as temporary_folder, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for example in found:
            built, (_, data) = built_page(example, temporary_folder), example_data(example)
            for width in WIDTHS:
                for scheme in ("light", "dark"):
                    page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=scheme)
                    page.goto(built.as_uri())
                    for level in data["levels"]:
                        open_level(page, level["id"])
                        page.locator(f'#level-{level["id"]} .node').first.dispatch_event("click")
                        fit = page.evaluate(FITS)
                        if fit["wide"] > width:
                            raise Refused(f'{example}: {level["id"]} is {fit["wide"]} px wide at {width} px, {scheme}')
                        if fit["cut"]:
                            raise Refused(f'{example}: {level["id"]} cuts {fit["cut"][0]} at {width} px, {scheme}')
                    for item in data["items"]:
                        open_item(page, item["key"])
                        for step in range(max(len(item["steps"]), 1)):
                            fit = page.evaluate(FITS)
                            if fit["wide"] > width or fit["cut"]:
                                raise Refused(f'{example}: {item["key"]} step {step + 1} does not fit {width} px, {scheme}: {fit["cut"][:1]}')
                            if step + 1 < len(item["steps"]):
                                page.locator(f'#{item["key"]} .bar-next').click()
                    page.close()
        browser.close()
    print(f"layout ok {len(found)}")
    print("Every level and every step of every page fits 390 and 1200 px in light and dark, and cuts no text.")


def capture(page_path, folder):
    from playwright.sync_api import sync_playwright
    folder = pathlib.Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 900}, color_scheme="light")
        page.goto(pathlib.Path(page_path).resolve().as_uri())
        # the frame's room below the last section is empty, and a full-page capture would show it
        page.add_style_tag(content=".frame-body::after { display: none; }")
        page.screenshot(path=str(folder / "1-first-screen.png"))
        # the first screen may hold only states, and this capture is the one place to show a part
        with_part = page.evaluate("data.levels.find(level => level.nodes.some(node => !node.state))?.id")
        if with_part:
            open_item(page, f"level-{with_part}")
        page.locator('.level:not(.away) .node[data-shape="part"]' if with_part else ".level:not(.away) .node").first.dispatch_event("click")
        page.screenshot(path=str(folder / "2-node-detail.png"), full_page=True)
        items = page.evaluate("data.items || []")
        moved = lambda item: len(item["steps"]) > 1
        chosen = [("3-scenario-step.png", next((item for item in items if item["kind"] == "Scenario" and moved(item)), None)), ("4-rule.png", next((item for item in items if item.get("verdict") == "pass"), None)),
                  ("5-counterexample-step.png", next((item for item in items if item.get("verdict") == "counterexample" and moved(item)), None))]
        for name, item in chosen:
            if item:
                open_item(page, item["key"])
                if moved(item) and "step" in name:
                    page.locator(f'#{item["key"]} .bar-next').click()
                page.screenshot(path=str(folder / name), full_page=True)
        browser.close()
    print(f"wrote {2 + sum(item is not None for _, item in chosen)} PNGs into {folder}")


def main(args):
    try:
        if len(args) == 2 and args[0] == "--check":
            check(args[1])
        elif len(args) == 2 and args[0] == "--layout":
            layout(args[1])
        elif len(args) == 3 and args[0] == "--capture":
            capture(args[1], args[2])
        elif len(args) in (2, 3) and not any(argument.startswith("-") for argument in args):
            pathlib.Path(args[-1]).write_text(build(*args[:-1]), encoding="utf-8")
            print(f"wrote {args[-1]}")
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except (Refused, OSError) as e:
        print(f"refused: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

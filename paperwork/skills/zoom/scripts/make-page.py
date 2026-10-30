#!/usr/bin/env python3
"""Build the clickable HTML page of one Schema document; it runs no proof.

usage: make-page.py DOC.json OUT.html       one self-contained page; refused when the document breaks the grammar, a
                                              chart has a name it cannot place or a scenario
                                              leaves the edges
       make-page.py --check DIR             build every DIR/X/schema.json, check the page in headless Chromium and print
                                              "ok N", then "<fact> ok" for each fact it measured on every page; a kept
                                              DIR/X/page.html must equal the page built
       make-page.py --layout DIR            measure every level of every DIR/X/'s page at 390 and 1200 px, light and
                                              dark, and print "layout ok N"
       make-page.py --capture PAGE.html DIR write the page's screens as numbered PNGs at 1200 px
                                              (every call with -- needs playwright: uv run --with playwright==1.64.1
                                              python3 make-page.py ...)

Exit status 0 means done, 1 a refusal, 2 a usage error.
"""
import html
import json
import pathlib
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))

from page import frame  # noqa: E402
from schema.model import Model, shape  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "page.html"
WIDTHS = (390, 1200)
PANEL_STATE = "document.querySelector('.detail:not([hidden])') === null"
PANEL_CHANGE = "document.querySelector('.level:not(.away) .node').dispatchEvent(new MouseEvent('click', {bubbles: true}))"
RESPONSE_PATHS = ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "<form", "<input", "<textarea", "<select")
LEGEND = {
    "state": ('<rect x="1" y="1" width="26" height="14" rx="7"/>', "State: where a thing is now"),
    "part": ('<rect x="1" y="1" width="26" height="14" rx="1"/>', "Part: a piece of the system"),
    "transition": ('<line x1="1" y1="8" x2="27" y2="8"/>', "Transition: a move between states"),
    "call": ('<line x1="1" y1="8" x2="27" y2="8" stroke-dasharray="5 4"/>', "Call: one part uses another"),
}


class Refused(Exception):
    pass


def unplaced(model):
    """What a chart cannot draw, each a sentence, since the page runs none of the structure checks."""
    for level_id, level in model.levels.items():
        here, lanes = {node["id"] for node in level["nodes"]}, {lane["id"] for lane in level.get("regions", []) + level.get("areas", [])}
        initial = level.get("initial", [])
        for edge in level["edges"]:
            yield from (f'{level_id}: {edge["label"]} ends on {end}, no node of this level' for end in (edge["from"], edge["to"]) if end not in here)
        for node in level["nodes"]:
            yield from (f'{level_id}: {node["id"]} sits in {lane}, no region or area of this level' for lane in (node.get("region"), node.get("area")) if lane and lane not in lanes)
        yield from (f'{level_id}: {start} starts no node of this level' for start in ([initial] if isinstance(initial, str) else initial) if start not in here)


def load(path):
    """The document's model, or Refused naming the first thing that stops the page."""
    try:
        document = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except ValueError as e:
        raise Refused(f"not a JSON document: {e}")
    if wrong := shape(document):
        raise Refused(f"{path}: {wrong[0][1]}")
    model = Model(document)
    if wrong := next(unplaced(model), None):
        raise Refused(f"{path}: {wrong}")
    for scenario in document["scenarios"]:
        if wrong := model.walk(scenario)[1]:
            raise Refused(f"{path}: {wrong[0]}")
    return model


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


def page_data(model):
    return {"levels": [level_data(model, level_id) for level_id in model.levels],
            "rules": {rule["slug"]: {"kind": rule["kind"], **rule["meta"]} for rule in model.document["rules"]}}


def trail(model, level_id):
    """The links from the root to this level, so a reader always sees where they are and can go back."""
    chain, opener = [], model.parent[level_id]
    while opener:
        chain.insert(0, model.node_level[opener])
        opener = model.parent[chain[0]]
    return " <span aria-hidden=\"true\">›</span> ".join(f'<a href="#level-{escape(step)}">{escape(model.levels[step]["title"])}</a>' for step in chain)


def legend(level, states):
    kinds = ["state"] * bool(states) + ["part"] * (len(level["nodes"]) > len(states)) + sorted({edge["kind"] for edge in level["edges"]}, reverse=True)
    return '<ul class="legend" aria-label="What the shapes mean">' + "".join(
        f'<li class="key-{kind}"><svg viewBox="0 0 28 16" width="28" height="16" aria-hidden="true">{LEGEND[kind][0]}</svg>{escape(LEGEND[kind][1])}</li>' for kind in kinds) + "</ul>"


def section(model, level_id):
    level = model.levels[level_id]
    crumbs = trail(model, level_id) or escape(model.document["title"])
    return (f'<section class="level" id="level-{escape(level_id)}">\n<p class="crumbs">{crumbs}</p>\n<h1>{escape(level["title"])}</h1>\n'
            f'<p class="lede">{escape(level["why"])}</p>\n<div class="chart" data-level="{escape(level_id)}"></div>\n{legend(level, model.states(level_id))}\n'
            '<div class="detail" hidden></div>\n</section>')


def navigation(model):
    rest = [(f"level-{level_id}", model.levels[level_id]["title"]) for level_id in model.levels if level_id != "root"]
    return [("level-root", model.levels["root"]["title"], rest) if rest else ("level-root", model.levels["root"]["title"])]


def build(path):
    model = load(path)
    sections = "\n".join(section(model, level_id) for level_id in model.levels)
    # the data goes in last, so no text of the document is read as a placeholder; a `<` could close or hide its script
    data = json.dumps(page_data(model), ensure_ascii=False).replace("<", "\\u003c")
    content = TEMPLATE.read_text(encoding="utf-8").replace("__SECTIONS__", sections).replace("__DATA__", data)
    return frame.build(model.document["title"], content, navigation(model))


def examples(folder):
    found = sorted(path for path in pathlib.Path(folder).iterdir() if (path / "schema.json").is_file())
    if not found:
        raise Refused(f"{folder}: no folder holds schema.json")
    return found


def built_page(example, temporary_folder):
    out = pathlib.Path(temporary_folder) / f"{example.name}.html"
    out.write_text(build(example / "schema.json"), encoding="utf-8")
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


FACTS = {"chart": chart, "detail panel": detail_panel, "level opens": level_opens, "read only": read_only}


def check(folder):
    from playwright.sync_api import sync_playwright
    found, failures = examples(folder), {}
    with tempfile.TemporaryDirectory() as temporary_folder, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for example in found:
            built, model = built_page(example, temporary_folder), load(example / "schema.json")
            for fact, why in frame.probe(browser, built.as_uri(), copied=level_data(model, "root")["copy"], change=PANEL_CHANGE, state=PANEL_STATE).items():
                failures.setdefault(fact, f"{example}: {why}")
            data = page_data(model)
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
  const clipped = [...section.querySelectorAll('h1, .crumbs, .lede, .legend li, .chart, .detail')].filter(box => box.scrollWidth > box.clientWidth + 1).map(box => box.className || box.tagName);
  const shapes = [...svg.querySelectorAll('.node')].filter(node => {
    const shape = node.querySelector('.shape').getBoundingClientRect();
    return [...node.querySelectorAll('text')].some(text => { const box = text.getBoundingClientRect(); return box.left < shape.left || box.right > shape.right; });
  }).map(node => node.dataset.id);
  const stray = innerWidth <= 820 && !document.querySelector('.frame-nav.open') ? [...document.querySelectorAll('.frame-nav a')].filter(link => link.checkVisibility({visibilityProperty: true})).map(link => link.textContent) : [];
  return {wide: document.documentElement.scrollWidth, cut: [...outside, ...clipped, ...shapes, ...stray]};
}"""


def layout(folder):
    from playwright.sync_api import sync_playwright
    found = examples(folder)
    with tempfile.TemporaryDirectory() as temporary_folder, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for example in found:
            built, data = built_page(example, temporary_folder), page_data(load(example / "schema.json"))
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
                    page.close()
        browser.close()
    print(f"layout ok {len(found)}")
    print("Every level of every page fits 390 and 1200 px in light and dark, and cuts no text.")


def capture(page_path, folder):
    from playwright.sync_api import sync_playwright
    folder = pathlib.Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 900}, color_scheme="light")
        page.goto(pathlib.Path(page_path).resolve().as_uri())
        page.screenshot(path=str(folder / "1-first-screen.png"))
        page.locator(".level:not(.away) .node").first.dispatch_event("click")
        page.screenshot(path=str(folder / "2-node-detail.png"), full_page=True)
        browser.close()
    print(f"wrote 2 PNGs into {folder}")


def main(args):
    try:
        if len(args) == 2 and args[0] == "--check":
            check(args[1])
        elif len(args) == 2 and args[0] == "--layout":
            layout(args[1])
        elif len(args) == 3 and args[0] == "--capture":
            capture(args[1], args[2])
        elif len(args) == 2 and not any(argument.startswith("-") for argument in args):
            pathlib.Path(args[1]).write_text(build(args[0]), encoding="utf-8")
            print(f"wrote {args[1]}")
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except (Refused, OSError) as e:
        print(f"refused: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

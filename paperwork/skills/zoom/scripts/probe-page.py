#!/usr/bin/env -S uv run -q --script
# /// script
# dependencies = ["playwright"]
# ///
"""Open a built page in installed Chrome and check what a reader sees.

usage: probe-page.py labels <page>       print each level's node and edge labels, the same on any engine build, and its
                                         history mark (H or H*) where it has one, and each final state as `final <label>`
       probe-page.py zoom <page>         `zoom: ok` when clicking a node that opens a level shows that level and the first
                                         scenario steps through its walk, with no page error; else `zoom: fail` and why
       probe-page.py meta <page>         `meta: <n> shown, <k> missing`: every `meta` value of the page's document,
                                         looked for in its note as ../references/ui/formats.md displays it
       probe-page.py behaviours <page>   `<role> <behaviour>: ok` or `: fail` per behaviour ../references/show.md adopts

Exit status 0 when nothing fails or is missing, 1 otherwise, 2 on a usage error.
"""
import pathlib
import sys

DIFF = {"added": "+", "removed": "−", "changed": "~"}
FORMAT = {"text": str, "number": lambda value: str(int(value)) if float(value).is_integer() else str(value), "url": None,
          "ms": lambda value: f"{value} ms", "percent": lambda value: f"{value}%", "date": str, "bool": lambda value: "yes" if value else "no"}
RESERVED = {"note": str, "diff": lambda value: f"{DIFF.get(value, '?')} {value}", "evidence": ", ".join, "constraint": ", ".join}


def shown(key, value):
    """The text formats.md says a reader sees for one entry, and the link it must carry, if any."""
    if key in RESERVED:
        return f"{key}: {RESERVED[key](value)}", None
    name, _, format_name = key.rpartition("-")
    if format_name == "url":
        return f"{name}: {name}", value
    return f"{name}: {FORMAT[format_name](value)}", None


class Page:
    def __init__(self, browser, path):
        self.errors = []
        self.browser_page = browser.new_page(viewport={"width": 1280, "height": 900})
        self.browser_page.on("pageerror", lambda e: self.errors.append(str(e)))
        # record what the page copies, since a file page's clipboard cannot be read back
        self.browser_page.add_init_script("window.__copied = []; if (navigator.clipboard) navigator.clipboard.writeText = t => (window.__copied.push(t), Promise.resolve());")
        self.browser_page.goto(pathlib.Path(path).resolve().as_uri())
        self.browser_page.wait_for_function("window.zoom && document.querySelector('.zoom-canvas svg')")

    def run_script(self, code, argument=None):
        return self.browser_page.evaluate(code, argument)

    def level(self):
        return self.run_script("document.getElementById('zoom').dataset.level")

    def go(self, level_id):
        self.run_script("id => window.zoom.goto(id)", level_id)
        self.browser_page.wait_for_function("id => document.getElementById('zoom').dataset.level === id", arg=level_id)

    def note(self):
        return self.run_script("(() => { const n = document.querySelector('.zoom-note'); return [n.innerText, n.innerHTML]; })()")


def model(page):
    return page.run_script("window.zoom.model")


def labels(page):
    lines = []
    # the level menu lists every level, on a page of any engine build, which may not hand its model out
    for level_id in page.run_script("[...document.querySelectorAll('.zoom-nav [data-l]')].map(b => b.dataset.l)"):
        page.go(level_id)
        got = page.run_script("""[...document.querySelectorAll('.zoom-canvas .node .n-lab')].map(t => 'node ' + t.textContent)
            .concat([...document.querySelectorAll('.zoom-canvas .edge .e-lab')].map(t => 'edge ' + t.textContent))
            .concat([...new Set([...document.querySelectorAll('.zoom-canvas .h-lab')].map(t => 'history ' + t.textContent))])
            .concat([...document.querySelectorAll('.zoom-canvas .node.final .n-lab')].map(t => 'final ' + t.textContent))""")
        lines += [f"{level_id}: {entry}" for entry in sorted(got)]
    print("\n".join(lines))
    return 0


def open_level(page):
    """Click a node of the first level that opens another, twice, as a reader does: select, then open."""
    zoom_model = model(page)
    page.go(zoom_model["root"])
    child = {level_entry["parent"]: level_entry["id"] for level_entry in zoom_model["levels"] if level_entry.get("parent")}
    root = next(level_entry for level_entry in zoom_model["levels"] if level_entry["id"] == zoom_model["root"])
    node_id = next((node["id"] for node in root["nodes"] if node["id"] in child), None)
    if not node_id:
        return "the top level has no node that opens a level"
    for _ in range(2):
        if page.level() == child[node_id]:
            break
        page.browser_page.click(f'.zoom-canvas .node[data-id="{node_id}"] .n-lab', force=True)
        page.browser_page.wait_for_timeout(150)
    return None if page.level() == child[node_id] else f"clicking {node_id} left the page at {page.level()}, not {child[node_id]}"


def scenario_steps(page):
    """Play the first scenario from its button, then step forward to its end and one step back."""
    zoom_model = model(page)
    if not zoom_model["scenarios"]:
        return "the document has no scenario"
    scenario = zoom_model["scenarios"][0]
    first = next((item["x"] for item in scenario["run"]["items"] if ":" not in item["x"]), None)   # an edge's key holds its level
    level_id = next((level["id"] for level in zoom_model["levels"] for node in level["nodes"] if node["id"] == first), zoom_model["root"])
    page.go(level_id)
    page.run_script("slug => document.querySelector(`[data-s=\"${slug}\"]`).click()", scenario["slug"])
    count = lambda: page.run_script("document.querySelector('.zoom-time output').textContent")
    try:
        page.browser_page.wait_for_function("() => !document.querySelector('.zoom-time').hidden", timeout=2000)
    except Exception:
        return f"playing {scenario['slug']} showed no step counter"
    at, n = map(int, count().split(" / "))
    if at != 1:
        return f"{scenario['slug']} started at step {at}"
    for step in range(2, n + 1):
        page.run_script("document.querySelector('.zoom-time [data-d=\"1\"]').click()")
        if count() != f"{step} / {n}":
            return f"next on {scenario['slug']} showed {count()}, not {step} / {n}"
    if n > 1:
        page.run_script("document.querySelector('.zoom-time [data-d=\"-1\"]').click()")
        if count() != f"{n - 1} / {n}":
            return f"back on {scenario['slug']} showed {count()}, not {n - 1} / {n}"
    return None


def copy_for_agent(page):
    """Select a node and copy it: the copied text names its level path, label and id."""
    zoom_model = model(page)
    page.go(zoom_model["root"])
    level = next(level for level in zoom_model["levels"] if level["id"] == zoom_model["root"])
    node = level["nodes"][0]
    page.run_script("id => window.zoom.select({ node: id })", node["id"])
    if not page.run_script("!!document.querySelector('.zoom-note .zoom-copy')"):
        return "the note has no copy button"
    page.browser_page.click(".zoom-note .zoom-copy")
    page.browser_page.wait_for_timeout(100)
    got = page.run_script("window.__copied")
    want = f"{level['title']} › {node['label']} ({node['id']})"
    return None if want in got else f"copied {got}, not {want!r}"


BEHAVIOURS = {"viewer open-level": open_level, "viewer scenario-steps": scenario_steps, "editor copy-for-agent": copy_for_agent}


def zoom(page):
    why = open_level(page) or scenario_steps(page) or ("; ".join(page.errors) if page.errors else None)
    print("zoom: ok" if not why else f"zoom: fail: {why}")
    return 1 if why else 0


def behaviours(page):
    failed = 0
    for name, probe in BEHAVIOURS.items():
        why = probe(page)
        print(f"{name}: ok" if not why else f"{name}: fail: {why}")
        failed += bool(why)
    return 1 if failed else 0


def meta(page):
    zoom_model = model(page)
    seen, missing = 0, []
    def look(where, meta_values):
        nonlocal seen
        text, html = page.note()
        for k, value in (meta_values or {}).items():
            want, href = shown(k, value)
            if want in text and (not href or f'href="{href}"' in html):
                seen += 1
            else:
                missing.append(f"{where}: {k}: {want}")
    for level in zoom_model["levels"]:
        page.go(level["id"])
        look(level["id"], level.get("meta"))
        if level["id"] == zoom_model["root"]:
            look("document", zoom_model.get("meta"))
        for node in level["nodes"]:
            if node.get("meta"):
                page.run_script("id => window.zoom.select({ node: id })", node["id"])
                look(f"{level['id']}: {node['id']}", node["meta"])
        for i, edge in enumerate(level["edges"]):
            if edge.get("meta"):
                page.run_script("([lid, i]) => { const L = window.zoom.model.levels.find(L => L.id === lid), e = L.edges[i];"
                      " const k = [...document.querySelectorAll('.zoom-canvas .edge')].find(g => g.getAttribute('aria-label').startsWith("
                      "L.nodes.find(n => n.id === e.from).label + ' to ' + L.nodes.find(n => n.id === e.to).label)).dataset.key;"
                      " window.zoom.select({ edge: k, e }); }", [level["id"], i])
                look(f"{level['id']}: {edge['from']}>{edge['to']}", edge["meta"])
    for entry in missing:
        print(f"missing {entry}")
    print(f"meta: {seen} shown, {len(missing)} missing")
    return 1 if missing else 0


def main(args):
    modes = {"labels": labels, "zoom": zoom, "meta": meta, "behaviours": behaviours}
    if len(args) != 2 or args[0] not in modes:
        print(__doc__, file=sys.stderr)
        return 2
    from playwright.sync_api import sync_playwright   # after the call is read, so a bad call answers without playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        try:
            return modes[args[0]](Page(browser, args[1]))
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

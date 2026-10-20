#!/usr/bin/env -S uv run -q --script
# /// script
# dependencies = ["playwright"]
# ///
"""zoom: open a built page in installed Chrome and check what a reader sees.

  probe-page.py labels <page>       print each level's node and edge labels, the same on any engine build
  probe-page.py zoom <page>         `zoom: ok` when clicking a node that opens a level shows that level and the first
                                    scenario steps through its walk, with no page error; else `zoom: fail` and why
  probe-page.py meta <page>         `meta: <n> shown, <k> missing`: every `meta` value of the page's document,
                                    looked for in its note as ../../formats.md displays it
  probe-page.py behaviours <page>   `<role> <behaviour>: ok` or `: fail` per behaviour ../../html.md adopts

Exit status 0 when nothing fails or is missing, 1 otherwise, 2 on a usage error.
"""
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

DIFF = {"added": "+", "removed": "−", "changed": "~"}
FORMAT = {"text": str, "number": lambda v: str(int(v)) if float(v).is_integer() else str(v), "url": None,
          "ms": lambda v: f"{v} ms", "percent": lambda v: f"{v}%", "date": str, "bool": lambda v: "yes" if v else "no"}
RESERVED = {"note": str, "diff": lambda v: f"{DIFF.get(v, '?')} {v}", "evidence": ", ".join, "constraint": ", ".join}


def shown(key, value):
    """The text formats.md says a reader sees for one entry, and the link it must carry, if any."""
    if key in RESERVED:
        return f"{key}: {RESERVED[key](value)}", None
    name, _, fmt = key.rpartition("-")
    if fmt == "url":
        return f"{name}: {name}", value
    return f"{name}: {FORMAT[fmt](value)}", None


class Page:
    def __init__(self, browser, path):
        self.errors = []
        self.p = browser.new_page(viewport={"width": 1280, "height": 900})
        self.p.on("pageerror", lambda e: self.errors.append(str(e)))
        # record what the page copies, since a file page's clipboard cannot be read back
        self.p.add_init_script("window.__copied = []; if (navigator.clipboard) navigator.clipboard.writeText = t => (window.__copied.push(t), Promise.resolve());")
        self.p.goto(pathlib.Path(path).resolve().as_uri())
        self.p.wait_for_function("window.zoom && document.querySelector('.zoom-canvas svg')")

    def js(self, code, arg=None):
        return self.p.evaluate(code, arg)

    def level(self):
        return self.js("document.getElementById('zoom').dataset.level")

    def go(self, lid):
        self.js("id => window.zoom.goto(id)", lid)
        self.p.wait_for_function("id => document.getElementById('zoom').dataset.level === id", arg=lid)

    def note(self):
        return self.js("(() => { const n = document.querySelector('.zoom-note'); return [n.innerText, n.innerHTML]; })()")


def model(pg):
    return pg.js("window.zoom.model")


def labels(pg):
    out = []
    # the level menu lists every level, on a page of any engine build, which may not hand its model out
    for lid in pg.js("[...document.querySelectorAll('.zoom-nav [data-l]')].map(b => b.dataset.l)"):
        pg.go(lid)
        got = pg.js("""[...document.querySelectorAll('.zoom-canvas .node .n-lab')].map(t => 'node ' + t.textContent)
            .concat([...document.querySelectorAll('.zoom-canvas .edge .e-lab')].map(t => 'edge ' + t.textContent))""")
        out += [f"{lid}: {x}" for x in sorted(got)]
    print("\n".join(out))
    return 0


def open_level(pg):
    """Click a node of the first level that opens another, twice, as a reader does: select, then open."""
    M = model(pg)
    pg.go(M["root"])
    child = {L["parent"]: L["id"] for L in M["levels"] if L.get("parent")}
    root = next(L for L in M["levels"] if L["id"] == M["root"])
    n = next((n["id"] for n in root["nodes"] if n["id"] in child), None)
    if not n:
        return "the top level has no node that opens a level"
    for _ in range(2):
        if pg.level() == child[n]:
            break
        pg.p.click(f'.zoom-canvas .node[data-id="{n}"] .n-lab', force=True)
        pg.p.wait_for_timeout(150)
    return None if pg.level() == child[n] else f"clicking {n} left the page at {pg.level()}, not {child[n]}"


def scenario_steps(pg):
    """Play the first scenario from its button, then step forward to its end and one step back."""
    M = model(pg)
    if not M["scenarios"]:
        return "the document has no scenario"
    s = M["scenarios"][0]
    first = next((it["x"] for it in s["run"]["items"] if ":" not in it["x"]), None)   # an edge's key holds its level
    lid = next((L["id"] for L in M["levels"] for n in L["nodes"] if n["id"] == first), M["root"])
    pg.go(lid)
    pg.js("slug => document.querySelector(`[data-s=\"${slug}\"]`).click()", s["slug"])
    count = lambda: pg.js("document.querySelector('.zoom-time output').textContent")
    try:
        pg.p.wait_for_function("() => !document.querySelector('.zoom-time').hidden", timeout=2000)
    except Exception:
        return f"playing {s['slug']} showed no step counter"
    at, n = map(int, count().split(" / "))
    if at != 1:
        return f"{s['slug']} started at step {at}"
    for k in range(2, n + 1):
        pg.js("document.querySelector('.zoom-time [data-d=\"1\"]').click()")
        if count() != f"{k} / {n}":
            return f"next on {s['slug']} showed {count()}, not {k} / {n}"
    if n > 1:
        pg.js("document.querySelector('.zoom-time [data-d=\"-1\"]').click()")
        if count() != f"{n - 1} / {n}":
            return f"back on {s['slug']} showed {count()}, not {n - 1} / {n}"
    return None


def copy_for_agent(pg):
    """Select a node and copy it: the copied text names its level path, label and id."""
    M = model(pg)
    pg.go(M["root"])
    L = next(L for L in M["levels"] if L["id"] == M["root"])
    n = L["nodes"][0]
    pg.js("id => window.zoom.select({ node: id })", n["id"])
    if not pg.js("!!document.querySelector('.zoom-note .zoom-copy')"):
        return "the note has no copy button"
    pg.p.click(".zoom-note .zoom-copy")
    pg.p.wait_for_timeout(100)
    got = pg.js("window.__copied")
    want = f"{L['title']} › {n['label']} ({n['id']})"
    return None if want in got else f"copied {got}, not {want!r}"


BEHAVIOURS = {"viewer open-level": open_level, "viewer scenario-steps": scenario_steps, "editor copy-for-agent": copy_for_agent}


def zoom(pg):
    why = open_level(pg) or scenario_steps(pg) or ("; ".join(pg.errors) if pg.errors else None)
    print("zoom: ok" if not why else f"zoom: fail: {why}")
    return 1 if why else 0


def behaviours(pg):
    failed = 0
    for name, probe in BEHAVIOURS.items():
        why = probe(pg)
        print(f"{name}: ok" if not why else f"{name}: fail: {why}")
        failed += bool(why)
    return 1 if failed else 0


def meta(pg):
    M = model(pg)
    seen, missing = 0, []
    def look(where, m):
        nonlocal seen
        text, html = pg.note()
        for k, v in (m or {}).items():
            want, href = shown(k, v)
            if want in text and (not href or f'href="{href}"' in html):
                seen += 1
            else:
                missing.append(f"{where}: {k}: {want}")
    for L in M["levels"]:
        pg.go(L["id"])
        look(L["id"], L.get("meta"))
        if L["id"] == M["root"]:
            look("document", M.get("meta"))
        for n in L["nodes"]:
            if n.get("meta"):
                pg.js("id => window.zoom.select({ node: id })", n["id"])
                look(f"{L['id']}: {n['id']}", n["meta"])
        for i, e in enumerate(L["edges"]):
            if e.get("meta"):
                pg.js("([lid, i]) => { const L = window.zoom.model.levels.find(L => L.id === lid), e = L.edges[i];"
                      " const k = [...document.querySelectorAll('.zoom-canvas .edge')].find(g => g.getAttribute('aria-label').startsWith("
                      "L.nodes.find(n => n.id === e.from).label + ' to ' + L.nodes.find(n => n.id === e.to).label)).dataset.key;"
                      " window.zoom.select({ edge: k, e }); }", [L["id"], i])
                look(f"{L['id']}: {e['from']}>{e['to']}", e["meta"])
    for m in missing:
        print(f"missing {m}")
    print(f"meta: {seen} shown, {len(missing)} missing")
    return 1 if missing else 0


def main(args):
    modes = {"labels": labels, "zoom": zoom, "meta": meta, "behaviours": behaviours}
    if len(args) != 2 or args[0] not in modes:
        print(__doc__)
        return 2
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        try:
            return modes[args[0]](Page(browser, args[1]))
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

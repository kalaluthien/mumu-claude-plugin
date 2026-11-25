#!/usr/bin/env python3
"""Replay the record card and search of `../page_parts.py` on a page of no skill, and on system's page through a copy of the plugin.

usage: replay-page-parts.py

page parts: a scratch page holding only lib's card and search parts, two boxes of its own and a contract of two nodes, one edge, a
property that holds and a gap on the first node; `drive-page-parts.cjs own` checks its badges, card, chips and search.
system reach: on a copy of the plugin whose lib card heads each card with a marked word and whose lib parts mark each badge group and
search hit they draw, system's `make-page.py` builds the first example's page, where `drive-page-parts.cjs system` finds the word in a
node's card heading, on every badge group and on every hit a search lists, and the words system hands the search as `SYSTEM_WORDS`
says: the box's placeholder, the empty search's group headings, and the heading over the first record of each kind its id finds;
no file of `skills/system/` outside its examples may hold the card or search code itself.
It prints `PASS <step>` or `FAIL <step>: <reason>` per step, then PASS or FAIL."""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

LIB = pathlib.Path(__file__).resolve().parents[1]
HERE = pathlib.Path(__file__).resolve().parent
PLUGIN = LIB.parent
sys.path.insert(0, str(LIB))
from page_parts import CARD, code, palette, style  # noqa: E402

CONTRACT = {
    "nodes": [{"id": "intake", "label": "Intake", "purpose": "takes each order"}, {"id": "ledger", "label": "Ledger", "purpose": "keeps each payment"}],
    "edges": [{"id": "intake-ledger", "from": "intake", "to": "ledger", "label": "writes to"}],
    "properties": [{"id": "checked", "title": "Every intake is checked", "kind": "invariant", "on": ["intake"], "statement": "An intake is checked once."},
                   {"id": "no-retry", "title": "A failed intake is never retried", "kind": "gap", "on": ["intake"], "statement": "Nothing retries an intake."}],
    "terms": [{"term": "ledger", "meaning": "the store of payments", "aliases": ["원장"]}],
}
PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Parts</title>
<style>
:root {{ --radius: 10px; --foreground: #111; --popover: #fff; --primary: #222; --primary-foreground: #fff; --muted: #eee; --muted-foreground: #666;
  --accent: #f2f2f2; --border: #ddd; --ring: #999; --canvas: #fafafa; --mark: #3366cc; --destructive: #c00; --ease: ease; --spring: ease;
  --shadow-md: none; --shadow-lg: none; --focus: none; }}
body {{ margin: 0; font: 14px/20px sans-serif; }}
.box {{ position: absolute; top: 80px; width: 160px; height: 60px; border: 1px solid; padding: 8px; }}
{style}
</style></head>
<body>
<div class="box" data-id="intake" style="left: 40px">Intake</div><div class="box" data-id="ledger" style="left: 240px">Ledger</div>
{card}
{palette}
<script type="application/json" id="data">{data}</script>
<script>
{code}
(() => {{
  const data = JSON.parse(document.getElementById("data").textContent), records = {{}}, counted = {{}};
  const make = (name, attributes = {{}}, ...children) => {{
    const element = document.createElement(name);
    for (const [key, value] of Object.entries(attributes)) key === "class" ? (element.className = value) : element.setAttribute(key, value);
    element.append(...children);
    return element;
  }};
  for (const [kind, list] of [["node", data.nodes], ["edge", data.edges], ["property", data.properties]]) for (const record of list) records[record.id] = {{ kind, record }};
  for (const property of data.properties) for (const one of property.on) ((counted[one] = counted[one] || {{}})[property.kind === "gap" ? "gap" : "holds"] = counted[one][property.kind === "gap" ? "gap" : "holds"] || []).push(property.id);
  let kept = null;
  const rows = id => {{ const {{ kind, record }} = records[id]; return [["purpose", "text", record.purpose || record.statement], ...(kind === "node" ? card.countRows(id) : [])]; }};
  const card = paperworkCard({{ make, formulas: {{}}, record: id => records[id], terms: () => data.terms, sources: () => [], counted: () => counted, rows,
    place: () => ({{ left: 480, top: 40, cost: 0, tied: 0 }}), kept: id => id === kept, light: () => {{}},
    follow: id => {{ if (records[id].kind !== "property") return false; kept = id; card.show(id); return true; }} }});
  for (const box of document.querySelectorAll(".box")) {{
    const badges = card.counts(box.dataset.id);
    if (badges) box.append(badges);
    box.addEventListener("pointerenter", () => card.show(box.dataset.id));
  }}
  const entries = Object.entries(records).map(([id, {{ kind, record }}]) => ({{ id, kind, name: record.label || record.title, note: kind,
    fields: [[record.label || record.title, 0], [id, 1], [record.purpose || record.statement, 3]], shown: [["purpose", record.purpose || record.statement]] }}));
  const search = paperworkSearch({{ make, entries: () => entries, terms: () => data.terms, shelf: () => "paperwork-parts-replay",
    kinds: {{ node: "Nodes", edge: "Edges", property: "Properties" }}, browse: [["Nodes", "node"]], open: entry => {{ kept = entry.id; card.show(entry.id); }} }});
  addEventListener("keydown", event => search.key(event));
}})();
</script>
</body></html>
"""
OWN = ("const spoken = piece =>", "const typed = text =>", "function measure(entry", "#card dl { margin", "#hits .hit { display")  # lines only the shared parts hold
MARK = "MARKED"
SYSTEM_WORDS = {"placeholder": "Search nodes, edges, scenarios and properties", "browse": ["Questions", "Scenarios", "Levels", "Properties"],
                "kinds": {"levels": "Levels", "areas": "Areas", "nodes": "Nodes", "edges": "Edges", "scenarios": "Scenarios", "properties": "Properties", "questions": "Questions"}}


def drive(*args):
    """The last line `drive-page-parts.cjs` printed for ARGS."""
    done = subprocess.run(["node", str(HERE / "drive-page-parts.cjs"), *args], capture_output=True, text=True, timeout=120)
    return (done.stdout.strip().splitlines() or [done.stderr.strip() or f"exit {done.returncode}"])[-1]


def page_parts():
    """Each reason the page of no skill failed to show the shared card and search."""
    with tempfile.TemporaryDirectory() as scratch:
        page = pathlib.Path(scratch) / "page.html"
        data = json.dumps(CONTRACT, ensure_ascii=False).replace("<", "\\u003c")
        page.write_text(PAGE.format(style=style(), card=CARD, palette=palette("Search"), data=data, code=code()))
        said = drive("own", str(page))
    return [] if said == "PASS own" else [said]


def system_reach():
    """Each reason system's page does not draw lib's card, or system keeps a copy of the shared code."""
    found = [f"{path.relative_to(PLUGIN)} holds `{mark}`" for path in sorted((PLUGIN / "skills" / "system").rglob("*")) if path.is_file()
             and "examples" not in path.parts and path.suffix in (".py", ".js", ".cjs", ".css") for mark in OWN if mark in path.read_text(errors="replace")]
    with tempfile.TemporaryDirectory() as scratch:
        copied = pathlib.Path(scratch) / "paperwork"
        shutil.copytree(PLUGIN, copied, ignore=shutil.ignore_patterns("page.html", "__pycache__"))
        part = copied / "lib" / "record-card.js"
        heading = 'make("h2", {}, '
        if not part.is_file() or heading not in part.read_text():
            return found + [f"the plugin holds no lib/record-card.js drawing a card heading by `{heading}`"]
        part.write_text(part.read_text().replace(heading, heading + f'"{MARK} ", '))
        for name, point, marked in (("record-card.js", 'make("span", { class: "counts", "data-for": id }', f'make("span", {{ class: "counts", "data-for": id, "data-mark": "{MARK}" }}'),
                                    ("record-search.js", "row.dataset.hit = entry.id;", f'row.dataset.hit = entry.id; row.dataset.mark = "{MARK}";')):
            source = (copied / "lib" / name).read_text()
            if source.count(point) != 1:
                return found + [f"lib/{name} holds no single `{point}` to mark"]
            (copied / "lib" / name).write_text(source.replace(point, marked))
        example = sorted((copied / "skills" / "system" / "examples").glob("*/contract.json"))[0]
        page = pathlib.Path(scratch) / "page.html"
        built = subprocess.run([sys.executable, str(copied / "skills" / "system" / "scripts" / "make-page.py"), str(example), str(page)], capture_output=True, text=True)
        if built.returncode:
            return found + [f"make-page.py on the copy failed: {(built.stdout + built.stderr).strip()}"]
        contract = json.loads(example.read_text())
        words = pathlib.Path(scratch) / "words.json"
        words.write_text(json.dumps({**SYSTEM_WORDS, "groups": [[contract[kind][0]["id"], contract[kind][0]["id"], heading] for kind, heading in SYSTEM_WORDS["kinds"].items()]}))
        said = drive("system", str(page), MARK, str(words))
        if said != "PASS system":
            found.append(said)
    return found


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    failed = False
    for step, run in (("page parts", page_parts), ("system reach", system_reach)):
        reasons = run()
        failed = failed or bool(reasons)
        print(f"FAIL {step}: {'; '.join(reasons)}" if reasons else f"PASS {step}")
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

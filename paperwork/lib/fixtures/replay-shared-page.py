#!/usr/bin/env python3
"""Replay one change to each rule of the shared page frame on a copy of the plugin, and fail when a page misses it or a skill keeps its own copy.

usage: replay-shared-page.py

examples: each of system's and flow's `examples/<name>/` holds a `contract.json` and the `page.html` its `make-page.py` builds from it.
written once: no file of either skill outside its examples holds a line only `../` holds of the card, search or frame, but the relay
starter `diagram-page.html`, whose frame block between its markers is the one `page_parts.frame()` writes.
one change: on a copy of the plugin whose `../record-card.js` heads each card with a planted word, `../record-search.css` fills a search
hit's mark with a planted colour, `../page-frame.js` marks each crumb and `../page-tokens.css` gives the light foreground token a planted
colour, each skill's `make-page.py` builds its first example and the copied `connect-page.py` refreshes the copied starter, and on all
three pages, each searched for its first node's label, `drive-shared-page.cjs` finds each change drawn and the search bar at the top right, in the same place, its placeholder
`Search <records>` and `/` opening it.
It prints `PASS <step>` or `FAIL <step>: <reason>` per step, then PASS or FAIL."""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

LIB = pathlib.Path(__file__).resolve().parents[1]
HERE = pathlib.Path(__file__).resolve().parent
PLUGIN = LIB.parent
sys.path.insert(0, str(LIB))
SKILLS = ("system", "flow")
STARTER = "skills/system/assets/diagram-page.html"
# lines only the shared parts hold, each in the file of lib/ named beside it
OWN = {"record-search.js": "const typed = text =>", "record-search.css": "#hits .hit { display", "record-card.js": "const GLYPHS = {",
       "record-card.css": "#card dl { margin", "page-frame.js": "window.paperworkFrame", "page-frame.css": "#crumbs .sep", "page-tokens.css": "--status-holds:"}
TITLE, MARK, INK = "PLANTED", "rgb(1, 2, 3)", "rgb(7, 8, 9)"
PLANTS = (("record-card.js", 'make("h2", {}, ', f'make("h2", {{}}, "{TITLE} ", '),
          ("record-search.css", "#hits mark { background: color-mix(in oklab, var(--mark) 18%, transparent);", f"#hits mark {{ background: {MARK};"),
          ("page-frame.js", '"data-level": id,', '"data-level": id, "data-planted": "crumb",'),
          ("page-tokens.css", "--foreground: oklch(.145 0 0);", f"--foreground: {INK};"))


def build(root, skill, contract, page):
    """Build CONTRACT's page into PAGE with ROOT's SKILL, and say why it failed or nothing."""
    done = subprocess.run([sys.executable, str(root / "skills" / skill / "scripts/make-page.py"), str(contract), str(page)], capture_output=True, text=True)
    return f"{skill}'s make-page.py on {contract.name}: {(done.stdout + done.stderr).strip()[-300:]}" if done.returncode else None


def examples(scratch):
    """Each skill whose samples are not each a contract and the page built from it under `examples/`."""
    found = []
    for skill in SKILLS:
        held = sorted((PLUGIN / "skills" / skill / "examples").glob("*/contract.json"))
        if not held:
            found.append(f"{skill} keeps no examples/<name>/contract.json")
        for contract in held:
            kept, built = contract.parent / "page.html", pathlib.Path(scratch) / f"{skill}-{contract.parent.name}.html"
            reason = build(PLUGIN, skill, contract, built)
            if reason or not kept.is_file() or kept.read_text() != built.read_text():
                found.append(reason or f"{skill}'s examples/{contract.parent.name}/page.html is not the page make-page.py builds")
    return found


def written_once():
    """Each skill file that holds shared code itself, and a starter whose frame block is not the current one."""
    found = [f"lib/{name} holds no `{line}`" for name, line in OWN.items() if line not in ((LIB / name).read_text() if (LIB / name).is_file() else "")]
    for skill in SKILLS:
        for path in sorted((PLUGIN / "skills" / skill).rglob("*")):
            if not path.is_file() or "examples" in path.parts or path.suffix not in (".py", ".js", ".cjs", ".css", ".html"):
                continue
            text = path.read_text(errors="replace")
            if path == PLUGIN / STARTER:
                text = re.sub(r"<!-- page frame -->.*?<!-- /page frame -->", "", text, flags=re.S)
            found += [f"{path.relative_to(PLUGIN)} holds `{line}`" for line in OWN.values() if line in text]
    try:
        from page_parts import frame
    except ImportError:
        return found + ["lib/page_parts.py holds no frame()"]
    if frame() not in (PLUGIN / STARTER).read_text():
        found.append(f"{STARTER} does not hold the frame block page_parts.frame() writes")
    return found


def one_change(scratch):
    """Each reason a planted change to the shared frame is not drawn on both skills' pages and the starter alike."""
    copied = pathlib.Path(scratch) / "paperwork"
    shutil.copytree(PLUGIN, copied, ignore=shutil.ignore_patterns("page.html", "__pycache__"))
    for name, point, planted in PLANTS:
        path = copied / "lib" / name
        if not path.is_file() or path.read_text().count(point) != 1:
            return [f"lib/{name} holds no single `{point}` to change"]
        path.write_text(path.read_text().replace(point, planted))
    pages, queries = [], []
    for skill in SKILLS:
        contract = sorted((copied / "skills" / skill / "examples").glob("*/contract.json"))[:1]
        page = pathlib.Path(scratch) / f"planted-{skill}.html"
        reason = build(copied, skill, contract[0], page) if contract else f"{skill} keeps no example"
        if reason:
            return [reason]
        pages.append(str(page))
        queries.append(json.loads(contract[0].read_text())["nodes"][0]["label"])
    done = subprocess.run([sys.executable, str(copied / "skills/system/scripts/connect-page.py"), str(copied / STARTER)], capture_output=True, text=True)
    if done.returncode:
        return [f"connect-page.py on the copied starter: {(done.stdout + done.stderr).strip()}"]
    pages.append(str(copied / STARTER))
    data = re.search(r'<script type="application/json" id="page-data">(.*?)</script>', (copied / STARTER).read_text(), re.S)
    queries.append(json.loads(data.group(1))["diagram-main"]["nodes"][0]["label"] if data else "")
    spec = pathlib.Path(scratch) / "spec.json"
    spec.write_text(json.dumps({"pages": pages, "queries": queries, "title": TITLE, "mark": MARK, "ink": INK}))
    done = subprocess.run(["node", str(HERE / "drive-shared-page.cjs"), str(spec)], capture_output=True, text=True, timeout=300)
    said = done.stdout.strip().splitlines()
    return [line[5:] for line in said if line.startswith("FAIL ")] or ([] if done.returncode == 0 and said else [(done.stderr.strip() or f"exit {done.returncode}")[-300:]])


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    failed = False
    with tempfile.TemporaryDirectory() as scratch:
        for step, run in (("examples", lambda: examples(scratch)), ("written once", written_once), ("one change", lambda: one_change(scratch))):
            reasons = run()
            failed = failed or bool(reasons)
            print(f"FAIL {step}: {'; '.join(reasons)}" if reasons else f"PASS {step}")
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

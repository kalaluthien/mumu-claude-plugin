#!/usr/bin/env python3
"""Write the pages in ../fixtures/, each a built page broken so one probe of probe-page.py fails.

usage: make-fixtures.py      build the meta-every-format page, then write from it
                             page-without-zoom.html          the node click handlers removed
                             page-missing-meta.html          one edge's `due-date` left out of its note
                             page-without-behaviours.html    node clicks, step buttons and the copy button removed

Run it after a change to the engine, so the fixtures break today's engine. Exit status 0, or 1 when a cut no
longer matches the engine, 2 on an argument.
"""
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "fixtures"
DOC = HERE.parents[2] / "schema" / "fixtures" / "meta-every-format.json"

CLICK = 'g.addEventListener("click", () => act(n.id, () => open && st.sel && st.sel.node === n.id ? goto(open, b) : select({ node: n.id })));'
GO = '.addEventListener("click", ev => { ev.stopPropagation(); goto(open, b); });'
CUTS = {
    "page-without-zoom.html": [(CLICK, ""), (GO, ";")],
    "page-missing-meta.html": [("${metaGrp(e.meta)}", '${metaGrp(Object.fromEntries(Object.entries(e.meta || {}).filter(([k]) => k !== "due-date")))}')],
    "page-without-behaviours.html": [(CLICK, ""), (GO, ";"),
                                     ('time.querySelectorAll("[data-d]").forEach(b => b.onclick = () => seek(+b.dataset.d));', ""),
                                     ('const cb = p.querySelector(".zoom-copy"); if (cb) cb.onclick = () => copy(cb);', ""),
                                     ("${copyFor(L, n.id, n.label)}", ""), ('${copyFor(L, st.sel.edge, e.label || "")}', "")],
}


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as d:
        view, page = pathlib.Path(d) / "view.json", pathlib.Path(d) / "page.html"
        for call in (["new", view], ["build", DOC, view, page]):
            subprocess.run([sys.executable, HERE / "make-diagram.py", *map(str, call)], check=True, capture_output=True)
        built = page.read_text(encoding="utf-8")
    # The fixtures sit beside the vendored font, so they point at it instead of each carrying a copy.
    built = re.sub(r"url\(data:font/woff2;base64,[^)]*\)", "url(../assets/fonts/poorstory.woff2)", built)
    OUT.mkdir(exist_ok=True)
    for name, cuts in CUTS.items():
        text = built
        for old, new in cuts:
            if old not in text:
                print(f"{name}: the engine no longer holds {old[:60]}")
                return 1
            text = text.replace(old, new)
        (OUT / name).write_text(text, encoding="utf-8")
        print("wrote", OUT / name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

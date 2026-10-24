#!/usr/bin/env python3
"""Check a Schema document and its view, build the zoom page, check the drawing.

usage: make-diagram.py new view.json                  write a minimal view of a Schema document
       make-diagram.py rules                          list the Schema's and the drawing's checks and the plan's parameters
       make-diagram.py plan doc.json view.json        print the plan in effect, marking what differs from the defaults
       make-diagram.py check doc.json view.json [--only a,b]   run the Schema's checks, then the drawing's
       make-diagram.py build doc.json view.json out.html   run the checks, then inline the joined model into the engine
       make-diagram.py render out.html [--shots DIR] [--font-css FILE]
       make-diagram.py make doc.json view.json out.html [--font-css FILE]   check, build, render; stop at the first failure

../../../schema/scripts/check-schema.py checks the document; this script draws it. A finding line is a defect of
the system the document describes, for the hand-over, never a failure. Exit status 0 means ok.
"""
import base64
import html
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
CHECKER = HERE.parents[2] / "schema" / "scripts" / "check-schema.py"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[6] / "lib"))

from page import view  # noqa: E402
from schema import checks  # noqa: E402
from schema import plan as params  # noqa: E402
from schema.model import Model, dump, shape  # noqa: E402


def read(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def check(spath, vpath, only=None):
    """The Schema's own check, then the drawing's: errors fail, warnings do not. Exit 0 ok, 1 errors."""
    if refusal := checks.unknown(only, view.CHECKS):
        print(refusal)
        return 2
    # the schema module owns its check: run its command rather than its code
    got = subprocess.run([sys.executable, str(CHECKER), "check", spath], capture_output=True, text=True)
    print("\n".join(line for line in got.stdout.splitlines() if line != "ok"))
    if got.returncode:
        print(f"{spath}: the Schema fails its checks, so it is not drawn")
        return 1
    failed = 0
    for name, problems, sev in view.run(read(spath), read(vpath), only):
        for p in problems:
            print(f"{'warning ' if sev == 'lint' else ''}view: {name}: {p}")
            failed += sev != "lint"
    print(f"{failed} problem(s)" if failed else "ok")
    return 1 if failed else 0


def prepare(s, v):
    """The joined model as the page reads it: the plan in effect, each Scenario's run, formulas laid out, and each
    rule's standing from Alloy's stored answers (Alloy is never started here)."""
    from schema import formula, prover
    from schema.model import flat, walk_steps
    model = flat(view.merge(s, v))   # the page reads the levels as one list
    model["plan"] = view.page_plan(model)
    schema_model = Model(model)
    schema_model.plan = model["plan"]
    by = {level["id"]: level for level in model["levels"]}
    # each Scenario's walk, resolved once here, so the page replays exactly what the checks and Alloy saw
    def key(k):
        level, e = schema_model.edges.get(k, (None, None))
        return f'{level["id"]}:{view.edge_key(by[level["id"]], e)}' if e else k   # a trigger's key is the same on both sides
    for x in model["scenarios"]:
        items = schema_model.walks[x["slug"]][0]
        x["run"] = {"items": [dict(it, x=key(it["x"])) for it in items],
                    "steps": [{"does": st.get("does", ""), "expects": st.get("expects", "")} for st in walk_steps(x["walk"])],
                    "uses": sorted(u for k, u in schema_model.footprint[x["slug"]] if k in ("op", "rule"))}
    world, _, res = prover.stored(schema_model) if schema_model.plan["prove"] != "off" else (prover.World(schema_model), None, None)
    found = prover.standing(schema_model, world, res)
    for x in model["rules"]:
        x["layout"] = formula.layout(x["formula"])
        x["role"], breaks = found[x["slug"]]
        if breaks:
            x["breaks"] = breaks
    for x in model["operations"]:
        for part in ("pre", "post"):
            if x.get(part):
                x[part + "Layout"] = formula.layout(x[part])
    return model


def build(spath, vpath, out):
    if check(spath, vpath):   # a model that fails its checks is not drawn
        return 1
    model = prepare(read(spath), read(vpath))
    page = (ASSETS / "zoom.html").read_text(encoding="utf-8")
    slots = {"TITLE": html.escape(model["title"]),
             "LANG": html.escape(model.get("lang", "en")),
             "CSS": (ASSETS / "zoom.css").read_text(encoding="utf-8"),
             "JS": (ASSETS / "zoom.js").read_text(encoding="utf-8"),
             "NEXT": html.escape(model.get("next", "")),
             "MODEL": json.dumps(model, ensure_ascii=False).replace("</", "<\\/"),
             "FONT": "data:font/woff2;base64," + base64.b64encode((ASSETS / "fonts" / "poorstory.woff2").read_bytes()).decode(),
             "LIMITS": (ASSETS / "phone-limits.json").read_text(encoding="utf-8")}
    page = re.sub(r"/\*(%s)\*/" % "|".join(slots), lambda m: slots[m.group(1)], page)   # one pass: a slot name inside a filled text stays
    pathlib.Path(out).write_text(page, encoding="utf-8")
    print("wrote", out)
    return 0


def render(path, shots=None, font_css=None):
    from page import drawing as r
    problems = r.check(path, shots, font_css)
    print("\n".join(problems) if problems else "ok")
    return 1 if problems else 0


def option(args, name):
    return args[args.index(name) + 1] if name in args else None


def main(args):
    cmd = args[0] if args else "help"
    if cmd == "new" and len(args) >= 2:   # a valid start: the reader's next step and one expected view drawn by the root
        start = {"next": "The reader's next action or choice, in one sentence.",
                 "plan": {"views": [{"name": "A diagram a practitioner expects", "level": "root"}]}}
        pathlib.Path(args[1]).write_text(dump(start) + "\n", encoding="utf-8")
        print("wrote", args[1], "(fields: assets/view-schema.json)")
        return 0
    if cmd == "rules":
        for name, rule, _ in checks.RULES + view.RULES:
            lint = name in (checks.LINT if name in checks.CHECKS else view.LINT)
            print(f"{name:13s} {'lint ' if lint else 'error'} {rule}")
        print()
        for name, (default, allowed, what) in (params.DEFAULTS | view.DEFAULTS).items():
            print(f"{name:13s} {json.dumps(default, ensure_ascii=False):30s} {what}")
        return 0
    if cmd == "plan" and len(args) >= 3:
        defaults = {k: d[0] for k, d in (params.DEFAULTS | view.DEFAULTS).items()}
        for name, value in view.page_plan(view.merge(read(args[1]), read(args[2]))).items():
            mark = "*" if value != defaults[name] else " "
            print(f"{mark} {name:11s} {json.dumps(value, ensure_ascii=False)}")
        return 0
    if cmd == "check" and len(args) >= 3:
        only = option(args, "--only")
        return check(args[1], args[2], only and only.split(","))
    if cmd == "build" and len(args) >= 4:
        return build(args[1], args[2], args[3])
    if cmd == "render" and len(args) >= 2:
        return render(args[1], option(args, "--shots"), option(args, "--font-css"))
    if cmd == "make" and len(args) >= 4:
        return build(args[1], args[2], args[3]) or render(args[3], None, option(args, "--font-css"))
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

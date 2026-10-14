#!/usr/bin/env python3
"""zoom-diagram: check a system model and its view, build the zoom diagram, check the drawing.

  make-diagram.py new view.json                  write a minimal view of a system model
  make-diagram.py rules                          list the system and drawing checks and the plan's parameters
  make-diagram.py plan system.json view.json     print the plan in effect, marking what differs from the defaults
  make-diagram.py check system.json view.json [--prove] [--only a,b]   run the checks; --prove adds Alloy
  make-diagram.py build system.json view.json out.html   run the checks, then inline the joined model into the engine
  make-diagram.py render out.html [--shots DIR] [--font-css FILE]
  make-diagram.py make system.json view.json out.html [--font-css FILE]   check, build, render; stop at the first failure
  make-diagram.py part system.json view.json part.html   the diagram as a part that show-me's assemble-page.py places

drill-it writes the system model (drill-it's check-system.py); this script draws it. A finding line is a
defect of the system the model describes, for the hand-over, never a failure. Exit status 0 means ok.
"""
import html
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
sys.path.insert(0, str(HERE.parents[4] / "lib"))

from diagram import view  # noqa: E402
from system import checks  # noqa: E402
from system import plan as params  # noqa: E402
from system.model import Model, dump, shape  # noqa: E402


def read(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def check(spath, vpath, prove=False, only=None):
    """The system's checks, then the drawing's; errors fail, lint warns, findings are reported; the last line says
    whether Alloy checked the model (with --prove). Exit 0 ok, 1 errors; Alloy never fails a run."""
    if refusal := checks.unknown(only, checks.CHECKS | view.CHECKS):
        print(refusal)
        return 2
    s, v = read(spath), read(vpath)
    if wrong := shape(s):   # the files' shape comes first: nothing else can be read until it fits
        print("FAIL  form\n" + "\n".join(f"      - {p}" for p in wrong) + f"\n{len(wrong)} problem(s)")
        return 1
    M = Model(s)
    mine = only and [x for x in only if x in checks.CHECKS]
    rows = checks.run(M, prove, mine) if not only or mine else []
    if not only or any(x in view.CHECKS or x == "form" for x in only):
        rows += [(("view-form" if name == "form" else name), p, sev) for name, p, sev in view.run(s, v, only)]
    lines, failed = checks.report(rows, M)
    print("\n".join(lines))
    items = M.m["scenarios"] + M.m["operations"] + M.m["rules"] + list(M.nodes.values())
    print(f"info  {sum(1 for x in items if x.get('refs'))}/{len(items)} elements cite a source")
    if failed:
        print(f"{failed} problem(s)")
        return 1
    status = getattr(M, "alloy_status", "")
    print(f"ok ({status})" if status.startswith("unproved") else "ok")
    return 0


def prepare(s, v):
    """The joined model as the page reads it: the plan in effect, each Scenario's run, formulas laid out, and each
    rule's standing from Alloy's stored answers (Alloy is never started here)."""
    from system import formula, prover
    from system.model import flat, walk_steps
    model = flat(view.merge(s, v))   # the page reads the levels as one list
    model["plan"] = view.page_plan(model)
    M = Model(model)
    M.plan = model["plan"]
    by = {L["id"]: L for L in model["levels"]}
    # each Scenario's walk, resolved once here, so the page replays exactly what the checks and Alloy saw
    def key(k):
        L, e = M.edges.get(k, (None, None))
        return f'{L["id"]}:{view.edge_key(by[L["id"]], e)}' if e else k   # a trigger's key is the same on both sides
    for x in model["scenarios"]:
        items = M.walks[x["slug"]][0]
        x["run"] = {"items": [dict(it, x=key(it["x"])) for it in items],
                    "steps": [{"does": st.get("does", ""), "expects": st.get("expects", "")} for st in walk_steps(x["walk"])],
                    "uses": sorted(u for k, u in M.footprint[x["slug"]] if k in ("op", "rule"))}
    W, _, res = prover.stored(M) if M.plan["prove"] != "off" else (prover.World(M), None, None)
    found = prover.standing(M, W, res)
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
    page = (ASSETS / "zoom-diagram.html").read_text(encoding="utf-8")
    slots = {"TITLE": html.escape(model["title"]),
             "LANG": html.escape(model.get("lang", "en")),
             "CSS": (ASSETS / "zoom-diagram.css").read_text(encoding="utf-8"),
             "JS": (ASSETS / "zoom-diagram.js").read_text(encoding="utf-8"),
             "NEXT": html.escape(model.get("next", "")),
             "MODEL": json.dumps(model, ensure_ascii=False).replace("</", "<\\/"),
             "LIMITS": (ASSETS / "phone-limits.json").read_text(encoding="utf-8")}
    page = re.sub(r"/\*(%s)\*/" % "|".join(slots), lambda m: slots[m.group(1)], page)   # one pass: a slot name inside a filled text stays
    pathlib.Path(out).write_text(page, encoding="utf-8")
    print("wrote", out)
    return 0


def part(spath, vpath, out):
    """The diagram as a page part: a mount point and the call that fills it once the page's scripts, the engine among
    them, have run; the page carries the engine, its fonts and the reader's next step."""
    model = json.dumps(prepare(read(spath), read(vpath)), ensure_ascii=False).replace("</", "<\\/")
    limits = (ASSETS / "phone-limits.json").read_text(encoding="utf-8").strip()
    pathlib.Path(out).write_text(
        '<div class="zd-part"></div>\n<script>addEventListener("DOMContentLoaded", (s => () => mountZoomDiagram('
        f"s.previousElementSibling, {model}, {limits}))(document.currentScript));</script>\n", encoding="utf-8")
    print("wrote", out)
    return 0


def render(path, shots=None, font_css=None):
    from diagram import drawing as r
    problems = r.check(path, shots, font_css)
    print("\n".join(problems) if problems else "ok")
    return 1 if problems else 0


def option(args, name):
    return args[args.index(name) + 1] if name in args else None


def main(args):
    cmd = args[0] if args else "help"
    if cmd == "new":   # a valid start: the reader's next step and one expected view drawn by the root
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
    if cmd == "plan":
        defaults = {k: d[0] for k, d in (params.DEFAULTS | view.DEFAULTS).items()}
        for name, value in view.page_plan(view.merge(read(args[1]), read(args[2]))).items():
            mark = "*" if value != defaults[name] else " "
            print(f"{mark} {name:11s} {json.dumps(value, ensure_ascii=False)}")
        return 0
    if cmd == "check":
        only = option(args, "--only")
        return check(args[1], args[2], "--prove" in args, only and only.split(","))
    if cmd == "build":
        return build(args[1], args[2], args[3])
    if cmd == "part":
        return part(args[1], args[2], args[3])
    if cmd == "render":
        return render(args[1], option(args, "--shots"), option(args, "--font-css"))
    if cmd == "make":
        return build(args[1], args[2], args[3]) or render(args[3], None, option(args, "--font-css"))
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

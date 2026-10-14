#!/usr/bin/env python3
"""zoom-diagram: check a model, build its zoom diagram, check the drawing.

  make-diagram.py new model.json                 write a valid minimal model
  make-diagram.py rules                          list the model checks and the plan's parameters
  make-diagram.py plan model.json                print the plan in effect, marking what differs from the defaults
  make-diagram.py check model.json [--quick] [--only a,b]   run the model checks; --quick leaves Alloy out
  make-diagram.py alloy model.json out.als       write the model as an Alloy 6 module
  make-diagram.py alloy --fetch                  download Alloy 6 for the alloy check (needs Java)
  make-diagram.py build model.json out.html      inline the model into the engine
  make-diagram.py render out.html [--shots DIR] [--font-css FILE]
  make-diagram.py make model.json out.html [--font-css FILE]   check, build, render; stop at the first failure

Exit status 0 means ok.
"""
import html
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
sys.path.insert(0, str(HERE.parents[4] / "lib"))

from diagram import checks  # noqa: E402
from diagram.model import dump, load  # noqa: E402


def check(path, prove=True, only=None):
    """Errors fail, lint warns; the last line says whether Alloy checked the model. Exit 0 ok, 1 errors, 3 no Alloy."""
    from diagram.model import shape
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if wrong := shape(data):   # the file's shape comes first: nothing else can be read until it fits
        print("FAIL  form\n" + "\n".join(f"      - {p}" for p in wrong) + f"\n{len(wrong)} problem(s)")
        return 1
    M = load(path)
    failed = 0
    for name, problems, sev in checks.run(M, prove, only):
        tag = "pass" if not problems else "FAIL" if sev == "error" else "warn"
        print(f"{tag:4s}  {name}" + (f"  ({M.alloy_status})" if name == "alloy" and M.alloy_status else ""))
        for p in problems:
            print(f"      - {p}")
        failed += len(problems) if sev == "error" else 0
    for n in getattr(M, "alloy_notes", []):
        print(f"note  {n}")
    items = M.m["scenarios"] + M.m["operations"] + M.m["rules"] + list(M.nodes.values())
    print(f"info  {sum(1 for x in items if x.get('refs'))}/{len(items)} elements cite a source")
    if failed:
        print(f"{failed} problem(s)")
        return 1
    print("ok" if M.alloy_status.startswith("checked") or only else f"ok (unproved: {M.alloy_status})")
    return 3 if "no Alloy" in M.alloy_status else 0


def prepare(model):
    """The model as the page reads it: the plan in effect, each Scenario's run, formulas laid out, and each
    rule's standing from Alloy's stored answers."""
    from diagram import formula, prover
    from diagram import plan as params
    from diagram.model import Model, flat, walk_steps
    model = flat(model)   # the page reads the levels as one list
    model["plan"] = params.effective(model)
    M = Model(model)
    # each Scenario's walk, resolved once here, so the page replays exactly what the checks and Alloy saw
    def key(k):
        L, e = M.edges.get(k, (None, None))
        if not e:
            return k   # a trigger's key is the same on both sides
        twins = sum(1 for x in L["edges"] if (x["from"], x["to"]) == (e["from"], e["to"]))
        return f'{L["id"]}:{e["from"]}>{e["to"]}' + (f'#{e["label"]}' if twins > 1 else "")
    for s in model["scenarios"]:
        items = M.walks[s["slug"]][0]
        s["run"] = {"items": [dict(it, x=key(it["x"])) for it in items],
                     "steps": [{"does": st.get("does", ""), "expects": st.get("expects", "")} for st in walk_steps(s["walk"])],
                     "uses": sorted(x for k, x in M.footprint[s["slug"]] if k in ("op", "rule"))}
    W, _, res = prover.solve(M) if M.plan["prove"] != "off" else (prover.World(M), None, None)
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


def build(path, out):
    model = prepare(json.loads(pathlib.Path(path).read_text(encoding="utf-8")))
    page = (ASSETS / "zoom-diagram.html").read_text(encoding="utf-8")
    for slot, text in (("/*TITLE*/", model["title"]),
                       ("/*LANG*/", html.escape(model.get("lang", "en"))),
                       ("/*CSS*/", (ASSETS / "zoom-diagram.css").read_text(encoding="utf-8")),
                       ("/*JS*/", (ASSETS / "zoom-diagram.js").read_text(encoding="utf-8")),
                       ("/*NEXT*/", html.escape(model.get("next", ""))),
                       ("/*MODEL*/", json.dumps(model, ensure_ascii=False)),
                       ("/*LIMITS*/", (ASSETS / "phone-limits.json").read_text(encoding="utf-8"))):
        page = page.replace(slot, text)
    pathlib.Path(out).write_text(page, encoding="utf-8")
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
    if cmd == "new":   # a valid start: one component level of two parts and one relation, and nothing else yet
        start = {"title": "System", "plan": {"intent": "The user's question, in one sentence.",
                                             "views": [{"name": "A diagram a practitioner expects", "level": "root"}]},
                 "scenarios": [], "operations": [], "rules": [],
                 "level": {"kind": "schema", "title": "System", "why": "What the system is made of.",
                           "nodes": [{"id": "a", "label": "Part", "what": "One sentence."},
                                     {"id": "b", "label": "Other part", "what": "One sentence."}],
                           "edges": [{"from": "a", "to": "b", "label": "uses", "what": "One sentence."}]}}
        pathlib.Path(args[1]).write_text(dump(start) + "\n", encoding="utf-8")
        print("wrote", args[1], "(fields: assets/model-schema.json)")
        return 0
    if cmd == "rules":
        for name, rule, _ in checks.RULES:
            print(f"{name:13s} {'lint ' if name in checks.LINT else 'error'} {rule}")
        from diagram import plan as params
        print()
        for name, (default, allowed, what) in params.DEFAULTS.items():
            print(f"{name:13s} {json.dumps(default, ensure_ascii=False):30s} {what}")
        return 0
    if cmd == "plan":
        from diagram import plan as params
        plan = load(args[1]).plan
        for name, value in plan.items():
            mark = "*" if value != params.DEFAULTS[name][0] else " "
            print(f"{mark} {name:11s} {json.dumps(value, ensure_ascii=False)}")
        return 0
    if cmd == "check":
        only = option(args, "--only")
        return check(args[1], "--quick" not in args, only and only.split(","))
    if cmd == "alloy":
        from diagram import prover as alloy
        if "--fetch" in args:
            print("wrote", alloy.fetch())
            return 0
        als, W, _ = alloy.translate(load(args[1]))
        pathlib.Path(args[2]).write_text(als, encoding="utf-8")
        print("\n".join(W.problems) or f"wrote {args[2]}")
        return 1 if W.problems else 0
    if cmd == "build":
        return build(args[1], args[2])
    if cmd == "render":
        return render(args[1], option(args, "--shots"), option(args, "--font-css"))
    if cmd == "make":
        return check(args[1]) or build(args[1], args[2]) or render(args[2], None, option(args, "--font-css"))
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Each check must be able to fail: one small mutation of a worked model per check, and the examples must pass.

Both sides are proved: drill-it's system checks and the drawing's checks, each example its system and view joined.
When the playbook is wrong (a check refuses something legitimate, a reference misses a case, the engine
draws badly), change the one file that owns it, never a single model, then run this and `make` every example.

usage: prove-checks.py [--prove]
  --prove   also run Alloy: the examples prove, and a must rule the behaviour can break is a finding (minutes)
"""
import copy
import json
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[4] / "lib"))
from diagram import view  # noqa: E402
from system import checks  # noqa: E402
from system import prover as alloy  # noqa: E402
from system.model import Model, levels_of, shape  # noqa: E402

EX = {p.name: view.merge(*(json.loads((p / f).read_text(encoding="utf-8")) for f in ("system.json", "view.json")))
      for p in (HERE.parent / "examples").iterdir() if p.is_dir()}


def step(at):
    return {"place": at, "does": "x", "expects": "y"}


def lv(m, lid):
    return next(L for L, opener in levels_of(m) if (opener or "root") == lid)


def node(m, nid):
    return next(n for L, _ in levels_of(m) for n in L["nodes"] if n["id"] == nid)


def sc(m, slug):
    return next(s for s in m["scenarios"] if s["slug"] == slug)


MUTATIONS = {
    "form": [("pull-request", lambda m: lv(m, "root").pop("initial")),
             ("pull-request", lambda m: lv(m, "push").update(partitions=lv(m, "push").pop("regions"))),
             ("pull-request", lambda m: lv(m, "open-s").update(regions=[{"id": "a", "label": "A"}])),
             ("pull-request", lambda m: m.update(next="")),
             ("pull-request", lambda m: m["plan"].pop("views")),
             ("pull-request", lambda m: m["plan"]["views"].append({"name": "x", "level": "nowhere"}))],
    "steps": ("pull-request", lambda m: sc(m, "land-change")["walk"].append(step("draft-s"))),
    "scoped": ("pull-request", lambda m: sc(m, "address-feedback")["walk"].append(step("open-s"))),
    "coverage": ("pull-request", lambda m: lv(m, "root")["edges"].append({"from": "draft-s", "to": "closed-s", "label": "abandon", "what": "x"})),
    "basis": ("pull-request", lambda m: m["scenarios"].append(dict(sc(m, "land-change"), slug="land-change-again"))),
    "placement": ("pull-request", lambda m: lv(m, "open-s")["edges"][0].update(ops=["PullRequest.comment"])),
    "explained": ("self", lambda m: [e.pop("what", None) for e in lv(m, "root")["edges"] if not e.get("rules")]),
    "size": ("pull-request", lambda m: lv(m, "root")["nodes"].extend({"id": f"x{i}", "label": f"Extra{i}", "x": 5, "y": i} for i in range(4))),
    "phone": ("ai-native-company", lambda m: lv(m, "root")["edges"].extend({"from": "lead", "to": t, "label": "steer", "what": "x"} for t in ("brain", "factory", "platform"))),
    "mechanism": ("ai-native-company", lambda m: sc(m, "solve-customer-problem").update(walk=[step("customers"), step("brain")])),
    "partitions": [("ai-native-company", lambda m: node(m, "judge").pop("partition")),
                   ("ai-native-company", lambda m: node(m, "customers").pop("partition"))],
    "quantities": [("recovery-trial", lambda m: next(e for e in lv(m, "root")["edges"] if e["from"] == "dex" and e["to"] == "died")["qty"].update(value=480)),
                   ("recovery-trial", lambda m: next(e for e in lv(m, "root")["edges"] if e["from"] == "dex" and e["to"] == "died").update(qty={"value": 28, "unit": "d", "kind": "delay"}))],
    "paths": ("pull-request", lambda m: [e.pop("mark", None) for e in lv(m, "open-s")["edges"]]),
    "four-states": [("pull-request", lambda m: lv(m, "push")["initial"].remove("matching")),   # Missing
                    ("pull-request", lambda m: lv(m, "push")["initial"].append("ahead")),   # Overloaded
                    ("pull-request", lambda m: lv(m, "push")["edges"].remove(next(e for e in lv(m, "push")["edges"] if e["to"] == "ahead"))),   # Illegal
                    ("pull-request", lambda m: lv(m, "push")["nodes"].append(dict(node(m, "ahead"), id="behind", label="Behind")) or lv(m, "push")["edges"].extend(  # Redundant
                        dict(e, **{k: "behind" for k in ("from", "to") if e[k] == "ahead"}) for e in list(lv(m, "push")["edges"]) if "ahead" in (e["from"], e["to"])))],
    "syncs": ("pull-request", lambda m: lv(m, "push")["syncs"][0].update(then="commit changes")),
    "depth": ("self", lambda m: m.update(plan={"depth": "overview", "views": [{"name": "levels", "level": "level"}], "why": {"depth": "x"}})),
    "naming": ("pull-request", lambda m: node(m, "push").update(label="Push")),
    "names": [("pull-request", lambda m: node(m, "push").update(label="밀어 넣기")),
              ("pull-request", lambda m: node(m, "push").setdefault("media", []).append({"type": "facts", "items": [["기준 커밋", "x"]]})),
              ("pull-request", lambda m: node(m, "push").setdefault("media", []).append({"type": "code", "title": "명령", "text": "x"})),
              ("pull-request", lambda m: m["screens"]["conversation"].update(title="대화"))],
    "media": ("pull-request", lambda m: node(m, "push").setdefault("media", []).append({"type": "payload", "text": "x"})),
    "facts": ("pull-request", lambda m: node(m, "push").setdefault("media", []).append({"type": "facts", "items": [["Question", m["plan"]["intent"]]]})),
    "prose": [("pull-request", lambda m: m.update(lang="ko", next="요청을 검사해요")),
              ("pull-request", lambda m: m.update(lang="ko", next="Alloy이 규칙을 풉니다.")),
              ("pull-request", lambda m: m.update(lang="ko", next="Alloy 가 규칙을 풉니다.")),
              ("pull-request", lambda m: m.update(lang="ko", next="위 그림을 봅니다."))],
    "unique-names": ("pull-request", lambda m: node(m, "push").update(label="Running checks")),
    "typed": ("pull-request", lambda m: next(o for o in m["operations"] if o["slug"] == "PullRequest.merge").update(sig="(method) → Commit")),
    "vocabulary": [("pull-request", lambda m: m["rules"][0].update(formula=m["rules"][0]["formula"] + " and fresh[pr]")),
                   ("pull-request", lambda m: node(m, "push").update(label="Now"))],
    "balanced": ("self", lambda m: lv(m, "check").pop("out")),
    "sources": ("self", lambda m: m["plan"].update(sources=["paperwork/lib/system/plan.py"], root=str(HERE.parents[5]))),   # real, uncited
}

# the sources check reads files, so its cases run in a scratch root: (name, plan, refs cited, text the problems must hold; None: pass)
FILES = {"a.md": "[b](b.md)\n", "b.md": "", "c.py": "from d import x\n", "d.py": "x = 1\n",
         "p/.claude-plugin/plugin.json": "{}", "p/skills/s.md": "run ${CLAUDE_PLUGIN_ROOT}/lib/t.py\n", "p/lib/t.py": ""}
ALL = ["a.md", "b.md", "c.py", "d.py"]
SOURCES = [
    ("all cited", {"sources": ALL}, ALL, None),
    ("uncited", {"sources": ALL}, ["a.md", "b.md", "c.py"], ["d.py: listed"]),
    ("link unlisted", {"sources": ["a.md"]}, ["a.md"], ["a.md links to b.md", "closure"]),
    ("import unlisted", {"sources": ["c.py"]}, ["c.py"], ["c.py imports d.py", "closure"]),
    ("plugin root unlisted", {"sources": ["p/skills/s.md"]}, ["p/skills/s.md"], ["p/skills/s.md names p/lib/t.py", "closure"]),
    ("plugin root listed", {"sources": ["p/skills/s.md", "p/lib/t.py"]}, ["p/skills/s.md", "p/lib/t.py"], None),
    ("excluded with reason", {"sources": ["a.md"], "exclude": {"b.md": "generated, never read"}}, ["a.md"], None),
    ("excluded, no reason", {"sources": ["a.md"], "exclude": {"b.md": ""}}, ["a.md"], ["b.md: give its exclusion a one-line reason"]),
    ("cited, unlisted", {"sources": ["a.md"], "exclude": {"b.md": "x"}}, ["a.md", "c.py"], ["cites c.py, which plan.sources does not list"]),
    ("design", {}, [], None),
]

# the one Alloy verdict that is kept, caught with --prove: a must rule the behaviour can break is a finding about
# the system, never a problem of the model
VERDICTS = [
    ("explore-unknowns", lambda m: op(m, "Question.close").pop("post"), "can break", "findings"),
]


def rule_of(m, slug):
    return next(i for i in m["rules"] if i["slug"] == slug)


def op(m, slug):
    return next(o for o in m["operations"] if o["slug"] == slug)


def failing(m, prove=False):
    s, v = view.split(m)
    rows = checks.run(Model(s), prove) + view.run(s, v)
    return {name for name, problems, _ in rows if problems}


def proved(m):
    """Alloy's notes and findings for a model's system side."""
    M = Model(view.split(m)[0])
    checks.run(M, True)
    return {"notes": M.alloy_notes, "findings": M.alloy_findings}


def source_cases():
    """What the sources check says for each case of SOURCES."""
    bad = []
    with tempfile.TemporaryDirectory() as root:
        for f, text in FILES.items():
            (pathlib.Path(root) / f).parent.mkdir(parents=True, exist_ok=True)
            (pathlib.Path(root) / f).write_text(text, encoding="utf-8")
        for name, plan, cited, expect in SOURCES:
            m = copy.deepcopy(EX["self"])
            m["plan"].update(plan, **({"root": root} if plan else {}))
            node(m, "elicit")["refs"] = [f"[{c}]({c}:1)" for c in cited]
            rows = {n: p for n, p, _ in checks.run(Model(view.split(m)[0]), only=["sources"])}
            if "sources" not in rows:
                bad.append(f"sources case {name}: no such check")
            elif expect is None and rows["sources"]:
                bad.append(f"sources case {name}: should pass, got {rows['sources']}")
            elif expect and not all(any(w in p for p in rows["sources"]) for w in expect):
                bad.append(f"sources case {name}: should report {expect}, got {rows['sources']}")
    return bad


def main(args):
    prove, bad = "--prove" in args, []
    if prove and not alloy.ready():
        print("--prove needs Alloy and Java: run drill-it's check-system.py alloy --fetch")
        return 1
    for name, m in sorted(EX.items()):
        if f := failing(m, prove):
            bad.append(f"example {name} fails {sorted(f)}")
    s = view.split(EX["pull-request"])[0]
    del s["scenarios"][0]["walk"]
    if shape(s) != ["system.scenarios[0]: missing walk"]:
        bad.append(f"shape: a missing field is not reported by its path, got {shape(s)}")
    for rule, _, _ in checks.RULES + view.RULES:
        if rule == "alloy":   # Alloy never fails a run: no mutation can make it fail
            continue
        if rule not in MUTATIONS:
            bad.append(f"{rule}: no mutation shows it can fail")
            continue
        cases = MUTATIONS[rule] if isinstance(MUTATIONS[rule], list) else [MUTATIONS[rule]]
        for k, (ex, mutate) in enumerate(cases):
            m = copy.deepcopy(EX[ex])
            mutate(m)
            if rule not in failing(m, prove):
                bad.append(f"{rule}: not caught by its mutation {k + 1} of {ex}")
    bad += [f"{r}: no such check" for r in MUTATIONS if r not in checks.CHECKS | view.CHECKS]   # a mutation of no check proves nothing
    bad += source_cases()
    if prove:
        for ex, mutate, words, where in VERDICTS:
            m = copy.deepcopy(EX[ex])
            mutate(m)
            got = proved(m)
            if not any(words in p for p in got[where]):
                bad.append(f"alloy: a mutation of {ex} should report '{words}' among its {where}, got {got}")
    n = len(checks.RULES) + len(view.RULES) - 1   # all but alloy
    print("\n".join(bad) if bad else f"ok: {n} checks, each caught its mutation" + (f"; {len(VERDICTS)} Alloy verdict caught" if prove else " (Alloy left out; use --prove)"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

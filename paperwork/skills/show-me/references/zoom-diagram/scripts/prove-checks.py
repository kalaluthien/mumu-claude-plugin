#!/usr/bin/env python3
"""Each check must be able to fail: one small mutation of a worked model per check, and the examples must pass.

When the playbook is wrong (a check refuses something legitimate, a reference misses a case, the engine
draws badly), change the one file that owns it, never a single model, then run this and `make` every example.

usage: prove-checks.py [--prove]
  --prove   also run Alloy: the examples prove, and each kind of Alloy verdict is caught by its mutation (minutes)
"""
import copy
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[4] / "lib"))
from diagram import checks  # noqa: E402
from diagram import prover as alloy  # noqa: E402
from diagram.model import Model, levels_of, shape  # noqa: E402

EX = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (HERE.parent / "examples").glob("*.json")}


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
    "syncs": ("pull-request", lambda m: lv(m, "push")["syncs"][0].update(then="commit changes")),
    "depth": ("self", lambda m: m.update(plan={"depth": "overview", "why": {"depth": "x"}})),
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
    "vocabulary": ("pull-request", lambda m: m["rules"][0].update(formula=m["rules"][0]["formula"] + " and fresh[pr]")),
    "balanced": ("self", lambda m: lv(m, "check").pop("out")),
    "alloy": ("pull-request", lambda m: rule_of(m, "fast-forward-push").update(formula="all branch: Branch | not branch.push")),
}

# each kind of Alloy verdict, caught with --prove: (example, mutation, words the problem must contain)
VERDICTS = [
    ("pull-request", lambda m: rule_of(m, "fast-forward-push").update(formula="all branch: Branch | not branch.push"), "cannot happen"),
    ("pull-request", lambda m: m["rules"].append(dict(rule_of(m, "three-dot"), slug="three-dot-again")) or node(m, "review-x").setdefault("rules", []).append("three-dot-again"), "follows from"),
    ("explore-unknowns", lambda m: op(m, "Question.close").pop("post"), "can break"),
    ("pull-request", lambda m: rule_of(m, "fast-forward-push").update(formula="no Branch and some Branch"), "contradict"),
]


def rule_of(m, slug):
    return next(i for i in m["rules"] if i["slug"] == slug)


def op(m, slug):
    return next(o for o in m["operations"] if o["slug"] == slug)


def failing(m, prove=False):
    return {name for name, problems, _ in checks.run(Model(m), prove) if problems}


def main(args):
    prove, bad = "--prove" in args, []
    if prove and not alloy.jar():
        print("--prove needs Alloy: run make-diagram.py alloy --fetch")
        return 1
    for name, m in sorted(EX.items()):
        if f := failing(m, prove):
            bad.append(f"example {name} fails {sorted(f)}")
    m = copy.deepcopy(EX["pull-request"])
    del m["scenarios"][0]["walk"]
    if shape(m) != ["model.scenarios[0]: missing walk"]:
        bad.append(f"shape: a missing field is not reported by its path, got {shape(m)}")
    for rule, _, _ in checks.RULES:
        if rule not in MUTATIONS:
            bad.append(f"{rule}: no mutation shows it can fail")
            continue
        if rule == "alloy" and not prove:
            continue
        cases = MUTATIONS[rule] if isinstance(MUTATIONS[rule], list) else [MUTATIONS[rule]]
        for k, (ex, mutate) in enumerate(cases):
            m = copy.deepcopy(EX[ex])
            mutate(m)
            if rule not in failing(m, prove):
                bad.append(f"{rule}: not caught by its mutation {k + 1} of {ex}")
    if prove:
        for ex, mutate, words in VERDICTS:
            m = copy.deepcopy(EX[ex])
            mutate(m)
            got = next(p for n, p, _ in checks.run(Model(m), True) if n == "alloy")
            if not any(words in p for p in got):
                bad.append(f"alloy: a mutation of {ex} should report '{words}', got {got}")
    n = len(checks.RULES) - (0 if prove else 1)
    print("\n".join(bad) if bad else f"ok: {n} checks, each caught its mutation" + (f"; {len(VERDICTS)} Alloy verdicts caught" if prove else " (Alloy left out; use --prove)"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Each drawing check must be able to fail: one small mutation of a worked example per check, and the examples
must pass. The Schema's own checks are proved beside the Schema (../../../schema/scripts/check-schema.py).

When a check refuses something legitimate or the engine draws badly, change the one file that owns it, never a
single example, then run this and `build` every example.

usage: prove-checks.py
"""
import copy
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
EXAMPLES = HERE.parents[3] / "examples"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[6] / "lib"))
from page import view  # noqa: E402
from schema.model import levels_of  # noqa: E402

EX = {p.name: view.merge(*(json.loads((p / f).read_text(encoding="utf-8")) for f in ("schema.json", "view.json")))
      for p in EXAMPLES.iterdir() if p.is_dir()}


def lv(m, lid):
    return next(L for L, opener in levels_of(m) if (opener or "root") == lid)


def node(m, nid):
    return next(n for L, _ in levels_of(m) for n in L["nodes"] if n["id"] == nid)


MUTATIONS = {
    "form": [("pull-request", lambda m: m.update(next="")),
             ("pull-request", lambda m: m["plan"].pop("views")),
             ("pull-request", lambda m: m["plan"]["views"].append({"name": "x", "level": "nowhere"}))],
    "size": ("pull-request", lambda m: lv(m, "root")["nodes"].extend({"id": f"x{i}", "label": f"Extra{i}", "x": 5, "y": i} for i in range(4))),
    "phone": ("ai-native-company", lambda m: lv(m, "root")["edges"].extend({"from": "lead", "to": t, "label": "steer", "what": "x"} for t in ("brain", "factory", "platform"))),
    "depth": ("self", lambda m: m.update(plan={"depth": "overview", "views": [{"name": "levels", "level": "level"}], "why": {"depth": "x"}})),
    "names": [("pull-request", lambda m: node(m, "push").update(label="밀어 넣기")),
              ("pull-request", lambda m: node(m, "push").setdefault("media", []).append({"type": "facts", "items": [["기준 커밋", "x"]]})),
              ("pull-request", lambda m: node(m, "push").setdefault("media", []).append({"type": "code", "title": "명령", "text": "x"})),
              ("pull-request", lambda m: m["screens"]["conversation"].update(title="대화"))],
    "facts": ("pull-request", lambda m: node(m, "push").setdefault("media", []).append({"type": "facts", "items": [["Question", m["plan"]["intent"]]]})),
    "prose": [("pull-request", lambda m: m.update(lang="ko", next="요청을 검사해요")),
              ("pull-request", lambda m: m.update(lang="ko", next="Alloy이 규칙을 풉니다.")),
              ("pull-request", lambda m: m.update(lang="ko", next="Alloy 가 규칙을 풉니다.")),
              ("pull-request", lambda m: m.update(lang="ko", next="위 그림을 봅니다."))],
}


def failing(m):
    return {name for name, problems, _ in view.run(*view.split(m)) if problems}


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    bad = [f"example {name} fails {sorted(f)}" for name, m in sorted(EX.items()) if (f := failing(m))]
    for rule in ["form"] + [name for name, _, _ in view.RULES]:
        if rule not in MUTATIONS:
            bad.append(f"{rule}: no mutation shows it can fail")
            continue
        cases = MUTATIONS[rule] if isinstance(MUTATIONS[rule], list) else [MUTATIONS[rule]]
        for k, (ex, mutate) in enumerate(cases):
            m = copy.deepcopy(EX[ex])
            mutate(m)
            if rule not in failing(m):
                bad.append(f"{rule}: not caught by its mutation {k + 1} of {ex}")
    bad += [f"{r}: no such check" for r in MUTATIONS if r not in view.CHECKS | {"form"}]   # a mutation of no check proves nothing
    print("\n".join(bad) if bad else f"ok: {len(view.RULES) + 1} drawing checks, each caught its mutation")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

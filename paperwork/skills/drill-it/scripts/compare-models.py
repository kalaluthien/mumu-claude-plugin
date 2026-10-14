#!/usr/bin/env python3
"""drill-it: compare an improved system model with its original.

  compare-models.py original.json improved.json

Prints `kept` or `dropped` for each Scenario and rule slug of the original, then each count criterion of the
improvement criteria (#511) on both models, then the improved model's check. An improvement keeps every slug and
passes the checks (no Alloy runs here); otherwise the exit status is 1.
"""
import json
import pathlib
import re
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "lib"))

from system import checks  # noqa: E402
from system.model import Model, shape  # noqa: E402


def norm(text):
    return re.sub(r"[\s_-]+", "", text).lower()


def cycles(L):
    """How many groups of a component level's nodes reach each other along its relations (Tarjan)."""
    succ = {n["id"]: [] for n in L["nodes"]}
    for e in L["edges"]:
        succ.setdefault(e["from"], []).append(e["to"])
    index, low, stack, on, found, k = {}, {}, [], set(), 0, [0]

    def visit(v):
        nonlocal found
        index[v] = low[v] = k[0]
        k[0] += 1
        stack.append(v)
        on.add(v)
        for w in succ.get(v, []):
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            group = []
            while True:
                w = stack.pop()
                on.discard(w)
                group.append(w)
                if w == v:
                    break
            found += len(group) > 1
    for v in list(succ):
        if v not in index:
            visit(v)
    return found


def counts(M):
    """Each count criterion of #511's table, as found on the model; lower is better unless the name says more."""
    m, levels = M.m, M.m["levels"]
    nodes = list(M.nodes.values())
    edges = [e for L in levels for e in L["edges"]]
    texts = [x.get("label", "") for x in nodes] + [x.get("what", "") for x in nodes + edges if x.get("what")]
    texts += [r["formula"] for r in m["rules"]]
    names = Counter(norm(x.get("label", "")) for x in nodes)
    crossing = {n: sum(1 for L in levels for e in L["edges"] if n in (e["from"], e["to"])) for n in M.child}
    deep = [len(M.levels[M.child[n]]["nodes"]) / (1 + crossing[n]) for n in M.child]
    part = {n["id"]: n.get("partition") for n in nodes}
    across = sum(1 for e in edges if part.get(e["from"]) and part.get(e["to"]) and part[e["from"]] != part[e["to"]])
    used = set().union(*M.footprint.values()) if M.footprint else set()
    handled = used | {("node", n) for r in m["rules"] for n in re.findall(r"\w+", r["formula"])}
    situations = {("trig", k) for k in M.trigs} | {("node", n["id"]) for L in levels if L["kind"] == "state" for n in L["nodes"]}
    returns = lambda o: "→" in o["sig"] and not re.search(r"→\s*(Nothing|Unit|None)?\s*$", o["sig"])
    return {
        "economy (nodes + edges + rules + operations)": len(nodes) + len(edges) + len(m["rules"]) + len(m["operations"]),
        "duplication (texts and formulas stated twice)": sum(c - 1 for c in Counter(t for t in texts if t).values() if c > 1),
        "one term per entity (nodes sharing a name)": sum(c - 1 for c in names.values() if c > 1),
        "deep modules (mean inner nodes / (1 + crossing edges), more is better)": round(sum(deep) / len(deep), 2) if deep else 0,
        "low coupling (edges across partitions / all edges)": round(across / len(edges), 2) if edges else 0,
        "cycles (component levels)": sum(cycles(L) for L in levels if L["kind"] == "schema"),
        "near-decomposability (most nodes on a level)": max(len(L["nodes"]) for L in levels),
        "nesting depth": max(M.depth(L["id"]) for L in levels),
        "requisite variety (triggers and states nothing handles)": len(situations - handled),
        "essential state (elements no Scenario uses)": len(M.elements() - used),
        "data/calculation/action (operations that return and change)": sum(1 for o in m["operations"] if returns(o) and (o.get("modifies") or o.get("post"))),
        "four states (Missing, Illegal, Redundant, Overloaded states found)": len(checks.four_states(M)),
    }


def main(args):
    if len(args) < 2:
        print(__doc__)
        return 2
    data = [json.loads(pathlib.Path(p).read_text(encoding="utf-8")) for p in args[:2]]
    if wrong := shape(data[1]):
        print("FAIL  form\n" + "\n".join(f"      - {p}" for p in wrong))
        return 1
    old, new = Model(data[0]), Model(data[1])
    dropped = 0
    for kind, items in (("scenario", "scenarios"), ("rule", "rules")):
        have = {x["slug"] for x in new.m[items]}
        for x in old.m[items]:
            state = "kept" if x["slug"] in have else "dropped"
            dropped += state == "dropped"
            print(f"{state:8s} {kind} {x['slug']}")
    added = [x["slug"] for items in ("scenarios", "rules") for x in new.m[items] if x["slug"] not in {y["slug"] for y in old.m[items]}]
    print(f"added    {', '.join(added) or 'none'}")
    a, b = counts(old), counts(new)
    print(f"\n{'count':72s} {'original':>9s} {'improved':>9s}")
    for k in a:
        print(f"{k:72s} {a[k]:>9} {b[k]:>9}")
    lines, failed = checks.report(checks.run(new), new)
    print("\n" + "\n".join(line for line in lines if not line.startswith("pass")))
    if failed:
        print(f"improved model fails its check: {failed} problem(s)")
    if dropped:
        print(f"{dropped} slug(s) dropped")
    return 1 if failed or dropped else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

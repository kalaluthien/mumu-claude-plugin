#!/usr/bin/env python3
"""Compare an improved Schema document with its original.

usage: compare-models.py original.json improved.json

Prints `kept` or `dropped` for each Scenario and rule slug of the original, then each count criterion of the
improvement criteria (#511) on both documents, then the improved document's check (../../schema/scripts/
check-schema.py). An improvement keeps every slug and passes the check (no Alloy runs here); otherwise the exit
status is 1.
"""
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
CHECKER = HERE.parent / "references" / "schema" / "scripts" / "check-schema.py"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))

from schema import checks  # noqa: E402
from schema.model import Model, shape  # noqa: E402


def norm(text):
    return re.sub(r"[\s_-]+", "", text).lower()


def cycles(level):
    """How many groups of a component level's nodes reach each other along its relations (Tarjan)."""
    succ = {n["id"]: [] for n in level["nodes"]}
    for e in level["edges"]:
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


def counts(model):
    """Each count criterion of #511's table, as found on the model; lower is better unless the name says more."""
    m, levels = model.m, model.m["levels"]
    nodes = list(model.nodes.values())
    edges = [e for level in levels for e in level["edges"]]
    texts = [x.get("label", "") for x in nodes] + [x.get("what", "") for x in nodes + edges if x.get("what")]
    texts += [r["formula"] for r in m["rules"]]
    names = Counter(norm(x.get("label", "")) for x in nodes)
    crossing = {n: sum(1 for level in levels for e in level["edges"] if n in (e["from"], e["to"])) for n in model.child}
    deep = [len(model.levels[model.child[n]]["nodes"]) / (1 + crossing[n]) for n in model.child]
    part = {n["id"]: n.get("partition") for n in nodes}
    across = sum(1 for e in edges if part.get(e["from"]) and part.get(e["to"]) and part[e["from"]] != part[e["to"]])
    used = set().union(*model.footprint.values()) if model.footprint else set()
    handled = used | {("node", n) for r in m["rules"] for n in re.findall(r"\w+", r["formula"])}
    situations = {("trig", k) for k in model.trigs} | {("node", n["id"]) for level in levels if level["kind"] == "state" for n in level["nodes"]}
    returns = lambda o: "→" in o["sig"] and not re.search(r"→\s*(Nothing|Unit|None)?\s*$", o["sig"])
    return {
        "economy (nodes + edges + rules + operations)": len(nodes) + len(edges) + len(m["rules"]) + len(m["operations"]),
        "duplication (texts and formulas stated twice)": sum(c - 1 for c in Counter(t for t in texts if t).values() if c > 1),
        "one term per entity (nodes sharing a name)": sum(c - 1 for c in names.values() if c > 1),
        "deep modules (mean inner nodes / (1 + crossing edges), more is better)": round(sum(deep) / len(deep), 2) if deep else 0,
        "low coupling (edges across partitions / all edges)": round(across / len(edges), 2) if edges else 0,
        "cycles (component levels)": sum(cycles(level) for level in levels if level["kind"] == "topology"),
        "near-decomposability (most nodes on a level)": max(len(level["nodes"]) for level in levels),
        "nesting depth": max(model.depth(level["id"]) for level in levels),
        "requisite variety (triggers and states nothing handles)": len(situations - handled),
        "essential state (elements no Scenario uses)": len(model.elements() - used),
        "data/calculation/action (operations that return and change)": sum(1 for o in m["operations"] if returns(o) and o.get("modifies")),
        "four states (Missing, Illegal, Redundant, Overloaded states found)": len(checks.four_states(model)),
    }


def main(args):
    if len(args) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    data = [json.loads(pathlib.Path(p).read_text(encoding="utf-8")) for p in args[:2]]
    if wrong := shape(data[1]):
        print("FAIL  form\n" + "\n".join(f"      - {text}" for _, text in wrong))
        return 1
    old, new = Model(data[0]), Model(data[1])
    dropped = 0
    for kind, items in (("scenario", "scenarios"), ("rule", "rules")):
        have = {x["slug"] for x in new.m[items]}
        for x in old.m[items]:
            state = "kept" if x["slug"] in have else "dropped"
            dropped += state == "dropped"
            print(f"{state:8s} {kind} {x['slug']}")
            now = next((y for y in new.m[items] if y["slug"] == x["slug"]), None)
            if now and any(now.get(k) != x.get(k) for k in ("formula", "walk", "text")):
                print(f"changed  {kind} {x['slug']}")
    added = [x["slug"] for items in ("scenarios", "rules") for x in new.m[items] if x["slug"] not in {y["slug"] for y in old.m[items]}]
    print(f"added    {', '.join(added) or 'none'}")
    a, b = counts(old), counts(new)
    print(f"\n{'count':72s} {'original':>9s} {'improved':>9s}")
    for k in a:
        print(f"{k:72s} {a[k]:>9} {b[k]:>9}")
    # the schema module owns its check: run its command rather than its code
    got = subprocess.run([sys.executable, str(CHECKER), "check", args[1]], capture_output=True, text=True)
    print("\n" + got.stdout.rstrip())
    failed = got.returncode
    if failed:
        print(f"improved document fails its check: {got.stderr.strip()}")
    if dropped:
        print(f"{dropped} slug(s) dropped")
    return 1 if failed or dropped else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

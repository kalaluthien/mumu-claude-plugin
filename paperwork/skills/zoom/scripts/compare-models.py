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


def normalize(text):
    return re.sub(r"[\s_-]+", "", text).lower()


def cycles(level):
    """How many groups of a component level's nodes reach each other along its relations (Tarjan)."""
    successors = {node["id"]: [] for node in level["nodes"]}
    for edge in level["edges"]:
        successors.setdefault(edge["from"], []).append(edge["to"])
    index, low, stack, on_stack, found, counter = {}, {}, [], set(), 0, [0]

    def visit(node):
        nonlocal found
        index[node] = low[node] = counter[0]
        counter[0] += 1
        stack.append(node)
        on_stack.add(node)
        for other in successors.get(node, []):
            if other not in index:
                visit(other)
                low[node] = min(low[node], low[other])
            elif other in on_stack:
                low[node] = min(low[node], index[other])
        if low[node] == index[node]:
            group = []
            while True:
                other = stack.pop()
                on_stack.discard(other)
                group.append(other)
                if other == node:
                    break
            found += len(group) > 1
    for root in list(successors):
        if root not in index:
            visit(root)
    return found


def counts(model):
    """Each count criterion of #511's table, as found on the model; lower is better unless the name says more."""
    document, levels = model.document, model.document["levels"]
    nodes = list(model.nodes.values())
    edges = [edge for level in levels for edge in level["edges"]]
    texts = [element.get("label", "") for element in nodes] + [element.get("what", "") for element in nodes + edges if element.get("what")]
    texts += [rule["formula"] for rule in document["rules"]]
    names = Counter(normalize(node.get("label", "")) for node in nodes)
    crossing = {node_id: sum(1 for level in levels for edge in level["edges"] if node_id in (edge["from"], edge["to"])) for node_id in model.child}
    deep = [len(model.levels[model.child[node_id]]["nodes"]) / (1 + crossing[node_id]) for node_id in model.child]
    part = {node["id"]: node.get("partition") for node in nodes}
    across = sum(1 for edge in edges if part.get(edge["from"]) and part.get(edge["to"]) and part[edge["from"]] != part[edge["to"]])
    used = set().union(*model.footprint.values()) if model.footprint else set()
    handled = used | {("node", token) for rule in document["rules"] for token in re.findall(r"\w+", rule["formula"])}
    situations = {("trig", trigger) for trigger in model.triggers} | {("node", node["id"]) for level in levels if level["kind"] == "state" for node in level["nodes"]}
    returns = lambda operation: "→" in operation["sig"] and not re.search(r"→\s*(Nothing|Unit|None)?\s*$", operation["sig"])
    return {
        "economy (nodes + edges + rules + operations)": len(nodes) + len(edges) + len(document["rules"]) + len(document["operations"]),
        "duplication (texts and formulas stated twice)": sum(count - 1 for count in Counter(text for text in texts if text).values() if count > 1),
        "one term per entity (nodes sharing a name)": sum(count - 1 for count in names.values() if count > 1),
        "deep modules (mean inner nodes / (1 + crossing edges), more is better)": round(sum(deep) / len(deep), 2) if deep else 0,
        "low coupling (edges across partitions / all edges)": round(across / len(edges), 2) if edges else 0,
        "cycles (component levels)": sum(cycles(level) for level in levels if level["kind"] == "topology"),
        "near-decomposability (most nodes on a level)": max(len(level["nodes"]) for level in levels),
        "nesting depth": max(model.depth(level["id"]) for level in levels),
        "requisite variety (triggers and states nothing handles)": len(situations - handled),
        "essential state (elements no Scenario uses)": len(model.elements() - used),
        "data/calculation/action (operations that return and change)": sum(1 for operation in document["operations"] if returns(operation) and operation.get("modifies")),
        "four states (Missing, Illegal, Redundant, Overloaded states found)": len(checks.four_states(model)),
    }


def main(args):
    if len(args) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    data = [json.loads(pathlib.Path(path).read_text(encoding="utf-8")) for path in args[:2]]
    if wrong := shape(data[1]):
        print("FAIL  form\n" + "\n".join(f"      - {text}" for _, text in wrong))
        return 1
    old, new = Model(data[0]), Model(data[1])
    dropped = 0
    for kind, items in (("scenario", "scenarios"), ("rule", "rules")):
        have = {entry["slug"] for entry in new.document[items]}
        for entry in old.document[items]:
            state = "kept" if entry["slug"] in have else "dropped"
            dropped += state == "dropped"
            print(f"{state:8s} {kind} {entry['slug']}")
            now = next((candidate for candidate in new.document[items] if candidate["slug"] == entry["slug"]), None)
            if now and any(now.get(field) != entry.get(field) for field in ("formula", "walk", "text")):
                print(f"changed  {kind} {entry['slug']}")
    added = [entry["slug"] for items in ("scenarios", "rules") for entry in new.document[items] if entry["slug"] not in {old_entry["slug"] for old_entry in old.document[items]}]
    print(f"added    {', '.join(added) or 'none'}")
    old_counts, new_counts = counts(old), counts(new)
    print(f"\n{'count':72s} {'original':>9s} {'improved':>9s}")
    for criterion in old_counts:
        print(f"{criterion:72s} {old_counts[criterion]:>9} {new_counts[criterion]:>9}")
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

#!/usr/bin/env python3
"""Replay the checker's `gaps` call on each example contract and each whole contract of this folder, and fail when a topic's count is not what the contract holds.

usage: replay-gap-counts.py

Each topic's count is worked out here apart from the checker, from the records the topic lands in. It prints one
FAIL line per contract whose counts differ, then one PASS or FAIL line for the examples and the folder, then whether a count it puts off
by one in one output is found, then PASS or FAIL."""
import collections
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from contract_levels import nested  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
CHECK = HERE.parent / "scripts" / "check-contract.py"
COUNT = re.compile(r"^ +(\d+)  (.+)$")


def counts(contract):
    """Each topic with the number of records of CONTRACT it counts."""
    levels = contract["levels"]
    group = {kind: [record for level in levels for record in level.get(kind, [])] for kind in ("nodes", "edges", "areas")}
    tags = {kind: collections.Counter(record.get("tag") for record in records) for kind, records in group.items()}
    claims = contract.get("claims", [])
    sourced = sum(1 for item in claims if "source" in item)
    items = collections.Counter(name for records in group.values() for record in records for name in record.get("info", {}))
    edge_items = sum(1 for edge in group["edges"] if edge.get("tag") in ("call", "publish", "access") and edge.get("info"))
    return {
        "components and their purpose": len(group["nodes"]) - tags["nodes"]["state"],
        "relations between components": len(group["edges"]) - tags["edges"]["transition"],
        "layers and hierarchy": len(levels) - 1,
        "partitioning and boundaries": len(group["areas"]),
        "naming and placement conventions": sourced,
        "coupling and dependency": tags["edges"]["dependsOn"] + sum(1 for item in claims if "paths" in item),
        "system documents": len(contract.get("sources", [])),
        "state": tags["nodes"]["state"] + tags["nodes"]["dataStore"] + tags["nodes"]["queue"],
        "control": sum(tags["nodes"][tag] for tag in ("trigger", "router", "policy")) + sum(tags["edges"][tag] for tag in ("transition", "triggers", "sequence", "governs")),
        "observation": items["signals"],
        "interfaces and payloads": tags["nodes"]["endpoint"] + edge_items,
        "failure and degraded behaviour": items["failure"] + items["errors"],
        "scenarios and operational principles": len(contract.get("scenarios", [])),
        "guarantees": sum(1 for item in claims if item["kind"] == "guarantee"),
        "assumptions and constraints": sum(1 for item in claims if item["kind"] == "assumption" or "source" in item),
        "domain terms and coined words": len(contract.get("terms", [])),
        "rationale": items["why"],
        "deployment and environment": tags["nodes"]["host"] + tags["areas"]["deployment"],
        "security and trust": tags["nodes"]["credential"] + tags["nodes"]["policy"] + tags["areas"]["trustZone"],
        "actors and outside systems": tags["nodes"]["actor"],
        "gaps and open questions": sum(1 for item in claims if "fault" in item),
        "evidence": sum(1 for records in group.values() for record in records if record.get("evidence")),
    }


def printed_counts(lines):
    """Each topic with the count the `gaps` output LINES prints for it."""
    return {match.group(2): int(match.group(1)) for match in map(COUNT.match, lines) if match}


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    failed, shifted = 0, None
    examples = sorted((HERE.parent / "examples").glob("*/contract.json"))
    held = [path for path in sorted(HERE.glob("*.json")) if "levels" in json.loads(path.read_text())]
    for where, contracts in (("examples", examples), ("fixtures", held)):
        wrong = 0
        for path in contracts:
            name, contract = path.parent.name if where == "examples" else path.stem, json.loads(path.read_text())
            lines = subprocess.run([sys.executable, str(CHECK), "gaps", str(path)], capture_output=True, text=True).stdout.splitlines()
            wanted, shown = counts(nested(contract)), printed_counts(lines)
            if shown != wanted:
                wrong += 1
                print(f"FAIL {name}: " + "; ".join(f"{topic} printed {shown.get(topic)}, holds {count}" for topic, count in wanted.items() if shown.get(topic) != count) + "".join(f"; {topic} printed, no topic" for topic in shown.keys() - wanted.keys()))
            shifted = shifted or (wanted, lines)
        failed += wrong or not contracts
        print(f"FAIL {where}: {wrong} of {len(contracts)} contracts with a count unlike what they hold" if wrong or not contracts else f"PASS {where}: each topic of {len(contracts)} contracts counts what they hold")
    found = False
    if shifted:
        wanted, lines = shifted
        k = next(k for k, line in enumerate(lines) if COUNT.match(line))
        found = printed_counts(lines[:k] + [COUNT.sub(lambda match: f"{int(match.group(1)) + 1:4d}  {match.group(2)}", lines[k])] + lines[k + 1:]) != wanted
    failed += not found
    print("PASS a count put off by one in one output is found" if found else "FAIL a count put off by one in one output is not found")
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

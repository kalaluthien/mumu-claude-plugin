#!/usr/bin/env python3
"""Replay one defect of each record every contract holds on a system and a flow fixture, and fail when the two checkers refuse it apart.

usage: replay-core-records.py

Each defect is planted in a copy of system's `parcel-locker.json` and of flow's `name-lookup.json`: both checkers must refuse it, by the
same rules with the same messages, a fixture's own source ids and node ids and labels left out, a break of `area-known` placed at its node
or area and compared by that rule alone; a copy holding a claim of each kind and each status, a status other than `holds` with its fault, must pass both; both `rules`
calls must word each rule of `../contract_core.py` alike; and both `fixtures` calls must pass, which hold each skill's own rules to the
copies that break them. It prints `PASS <step>` or `FAIL <step>: <reason>` per step, then PASS or FAIL."""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

LIB = pathlib.Path(__file__).resolve().parents[1]
SKILLS = LIB.parent / "skills"
sys.path.insert(0, str(LIB))
from contract_core import KINDS, RULES, STATUSES  # noqa: E402

MARKUP = "The planted text holds <b>markup</b>."
FIXTURES = {"system": SKILLS / "system/fixtures/parcel-locker.json", "flow": SKILLS / "flow/fixtures/name-lookup.json"}


def claim(**fields):
    return {"id": "planted", "title": "planted", "kind": "guarantee", "statement": "A planted claim holds.", **fields}


def spelt(contract):
    """A sentence that spells the first node's label where it should name the node as `{id}`."""
    return f"It is said of the {contract['nodes'][0]['label']}."


def opener(contract, skill, k):
    """The first record of the K-th level that may open a level: a node in system, an edge in flow."""
    level = contract["levels"][k]["id"]
    return next(record for record in contract["nodes" if skill == "system" else "edges"] if record["level"] == level)


def shared_node(contract):
    """The first node whose area holds another node too, so moving it out leaves its area held."""
    areas = [node.get("area") for node in contract["nodes"]]
    return next(node for node in contract["nodes"] if "area" in node and areas.count(node["area"]) > 1)


def empty_area(contract, skill):
    """An area no node sits in, of the form SKILL's areas take."""
    first = contract["areas"][0]
    return {"id": "planted-area", "label": "Planted", **({"tag": first["tag"], "level": first["level"]} if skill == "system" else {})}


# the kind and id of the record a defect's `area-known` break must be placed at, as `<kind>/<id>` or `<kind> <id>`; only that break
# is compared, since a node's says how far its skill's areas reach and moving a node out may break a skill's own rules
PLACED = {"an area holding no node": ("areas", lambda contract: "planted-area"), "a node naming no area": ("nodes", lambda contract: shared_node(contract)["id"])}

DEFECTS = {
    "a claim of an old kind": lambda contract, skill: contract["claims"].append(claim(kind="invariant")),
    "a claim of an old status": lambda contract, skill: contract["claims"].append(claim(status="broken")),
    "a status other than holds with no fault": lambda contract, skill: contract["claims"].append(claim(status="unknown")),
    "a written status beside paths": lambda contract, skill: contract["claims"].append(claim(status="holds", paths=[[contract["edges"][0]["id"]]] * 2)),
    "a properties list": lambda contract, skill: contract.update(properties=[]),
    "a source with no path": lambda contract, skill: contract["sources"].append({"id": "planted", "says": "It says."}),
    "a term with no meaning": lambda contract, skill: contract["terms"].append({"term": "planted"}),
    "an area holding no node": lambda contract, skill: contract["areas"].append(empty_area(contract, skill)),
    "a node naming no area": lambda contract, skill: shared_node(contract).update(area="no-such-area"),
    "a question with no answer": lambda contract, skill: contract["questions"].append({"id": "planted", "asks": "What is planted?"}),
    "an evidence entry naming no source": lambda contract, skill: contract["claims"][0].update(evidence=["no-such-source"]),
    "an id that is no slug": lambda contract, skill: contract["claims"].append(claim(id="Planted One")),
    "an area's evidence naming no source": lambda contract, skill: contract["areas"][0].update(evidence=["no-such-source"]),
    "a list of strings holding a number": lambda contract, skill: contract["claims"][0].update(evidence=[1]),
    "a list of strings holding a blank": lambda contract, skill: contract["claims"][0].update(evidence=[" "]),
    "markup in a term's meaning": lambda contract, skill: contract["terms"][0].update(meaning=MARKUP),
    "a label spelt in an area's purpose": lambda contract, skill: contract["areas"][0].update(purpose=spelt(contract)),
    "a label spelt in a level's about": lambda contract, skill: contract["levels"][0].update(about=spelt(contract)),
    "a label spelt in a claim's statement": lambda contract, skill: contract["claims"].append(claim(statement=spelt(contract))),
    "a label spelt in a claim's fault": lambda contract, skill: contract["claims"].append(claim(status="unknown", fault=spelt(contract))),
    "a label spelt in a question": lambda contract, skill: contract["questions"][0].update(asks=spelt(contract)),
    "a blank alias": lambda contract, skill: contract["terms"][0].update(aliases=[" "]),
    "a blank fault on a holding claim": lambda contract, skill: contract["claims"].append(claim(fault=" ")),
    "an opens naming no level": lambda contract, skill: opener(contract, skill, 0).update(opens="no-such-level"),
    "a chain of opens back to the first level": lambda contract, skill: opener(contract, skill, 1).update(opens=contract["levels"][0]["id"]),
}


def every_claim(contract, skill):
    contract["claims"] += [claim(id=f"planted-{kind}-{status}", title=f"planted-{kind}-{status}", kind=kind, status=status,
                                 **({} if status == "holds" else {"fault": "The planted claim has no source."})) for kind in KINDS for status in STATUSES]


def breaks(skill, contract, scratch):
    """The rule and message of each break SKILL's checker prints for CONTRACT, each id of its sources and each id and label of its nodes written as `<id>`."""
    target = pathlib.Path(scratch) / f"{skill}.json"
    target.write_text(json.dumps(contract))
    printed = subprocess.run([sys.executable, str(SKILLS / skill / "scripts/check-contract.py"), "check", str(target)], capture_output=True, text=True).stdout
    names = sorted({record[key] for kind in ("sources", "nodes") for record in contract[kind] for key in ("id", "label") if key in record}, key=len, reverse=True)
    found, places = set(), set()
    for line in printed.splitlines():
        parts = line.split(": ", 2)
        if len(parts) == 3:
            found.add((parts[1], re.sub(r"<id>(?:, <id>)*", "<id>", re.sub("|".join(map(re.escape, names)) or "$^", "<id>", parts[2]))))
            places.add((parts[0], parts[1]))
    return found, places


def rules(skill):
    printed = subprocess.run([sys.executable, str(SKILLS / skill / "scripts/check-contract.py"), "rules"], capture_output=True, text=True).stdout
    return {line.split(": ", 1)[0]: line for line in printed.splitlines() if ": " in line}


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    failed = False
    with tempfile.TemporaryDirectory() as scratch:
        for name, plant in [*DEFECTS.items(), ("a claim of each kind and each status", every_claim)]:
            found, misplaced = {}, []
            for skill, path in FIXTURES.items():
                contract = json.loads(path.read_text())
                plant(contract, skill)
                found[skill], places = breaks(skill, contract, scratch)
                if name in PLACED:
                    kind, key = PLACED[name][0], PLACED[name][1](json.loads(path.read_text()))
                    found[skill] = {(rule, "") for rule, _ in found[skill] if rule == "area-known"}
                    if not any(place.endswith((f"{kind}/{key}", f"{kind} {key}")) for place, rule in places if rule == "area-known"):
                        misplaced.append(f"{skill} places it at {sorted(places)}, not at its {kind} {key}")
            if plant is every_claim:
                reason = next((f"{skill} refuses it: {sorted(got)}" for skill, got in found.items() if got), None)
            elif not found["system"] or not found["flow"]:
                reason = f"a checker passes it: system {sorted(found['system'])}, flow {sorted(found['flow'])}"
            else:
                reason = None if found["system"] == found["flow"] else f"system says {sorted(found['system'])}, flow {sorted(found['flow'])}"
            reason = reason or "; ".join(misplaced) or None
            print(f"FAIL {name}: {reason}" if reason else f"PASS {name}")
            failed |= bool(reason)
    worded = {skill: rules(skill) for skill in FIXTURES}
    apart = [rule for rule in RULES if not worded["system"].get(rule) or worded["system"].get(rule) != worded["flow"].get(rule)]
    print(f"FAIL rules: {', '.join(apart)} worded apart or missing" if apart else "PASS rules")
    failed |= bool(apart)
    for skill in FIXTURES:
        done = subprocess.run([sys.executable, str(SKILLS / skill / "scripts/check-contract.py"), "fixtures"], capture_output=True, text=True)
        missed = [line for line in done.stdout.splitlines() if line.startswith("FAIL ")]
        print(f"FAIL {skill} fixtures: {'; '.join(missed) or f'exit {done.returncode}'}" if done.returncode else f"PASS {skill} fixtures")
        failed |= bool(done.returncode)
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

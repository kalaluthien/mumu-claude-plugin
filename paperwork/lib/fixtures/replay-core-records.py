#!/usr/bin/env python3
"""Replay one defect of each record every contract holds on a system and a flow fixture, and fail when the two checkers refuse it apart.

usage: replay-core-records.py

Each defect is planted in a copy of system's `parcel-locker.json` and of flow's `name-lookup.json`: both checkers must refuse it, by the
same rules with the same messages, a fixture's own list of source ids left out; a copy holding a claim of each kind and each status, a status
other than `holds` with its fault, must pass both; and both `rules` calls must word each rule of `../contract_core.py` alike. It prints
`PASS <step>` or `FAIL <step>: <reason>` per step, then PASS or FAIL."""
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

FIXTURES = {"system": SKILLS / "system/fixtures/parcel-locker.json", "flow": SKILLS / "flow/fixtures/name-lookup.json"}


def claim(**fields):
    return {"id": "planted", "title": "planted", "kind": "guarantee", "statement": "A planted claim holds.", **fields}


def empty_area(contract, skill):
    """An area no node sits in, of the form SKILL's areas take."""
    first = contract["areas"][0]
    return {"id": "planted-area", "label": "Planted", **({"tag": first["tag"], "level": first["level"]} if skill == "system" else {})}


DEFECTS = {
    "a claim of an old kind": lambda contract, skill: contract["claims"].append(claim(kind="invariant")),
    "a claim of an old status": lambda contract, skill: contract["claims"].append(claim(status="broken")),
    "a status other than holds with no fault": lambda contract, skill: contract["claims"].append(claim(status="unknown")),
    "a written status beside paths": lambda contract, skill: contract["claims"].append(claim(status="holds", paths=[[contract["edges"][0]["id"]]] * 2)),
    "a properties list": lambda contract, skill: contract.update(properties=[]),
    "a source with no path": lambda contract, skill: contract["sources"].append({"id": "planted", "says": "It says."}),
    "a term with no meaning": lambda contract, skill: contract["terms"].append({"term": "planted"}),
    "an area holding no node": lambda contract, skill: contract["areas"].append(empty_area(contract, skill)),
    "a question with no answer": lambda contract, skill: contract["questions"].append({"id": "planted", "asks": "What is planted?"}),
    "an evidence entry naming no source": lambda contract, skill: contract["claims"][0].update(evidence=["no-such-source"]),
    "an id that is no slug": lambda contract, skill: contract["claims"].append(claim(id="Planted One")),
}


def every_claim(contract, skill):
    contract["claims"] += [claim(id=f"planted-{kind}-{status}", title=f"planted-{kind}-{status}", kind=kind, status=status,
                                 **({} if status == "holds" else {"fault": "The planted claim has no source."})) for kind in KINDS for status in STATUSES]


def breaks(skill, contract, scratch):
    """The rule and message of each break SKILL's checker prints for CONTRACT, each id of its sources written as `<source>`."""
    target = pathlib.Path(scratch) / f"{skill}.json"
    target.write_text(json.dumps(contract))
    printed = subprocess.run([sys.executable, str(SKILLS / skill / "scripts/check-contract.py"), "check", str(target)], capture_output=True, text=True).stdout
    names = sorted((source["id"] for source in contract["sources"] if "id" in source), key=len, reverse=True)
    found = set()
    for line in printed.splitlines():
        parts = line.split(": ", 2)
        if len(parts) == 3:
            found.add((parts[1], re.sub(r"<source>(?:, <source>)*", "<source>", re.sub("|".join(map(re.escape, names)) or "$^", "<source>", parts[2]))))
    return found


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
            found = {}
            for skill, path in FIXTURES.items():
                contract = json.loads(path.read_text())
                plant(contract, skill)
                found[skill] = breaks(skill, contract, scratch)
            if plant is every_claim:
                reason = next((f"{skill} refuses it: {sorted(got)}" for skill, got in found.items() if got), None)
            elif not found["system"] or not found["flow"]:
                reason = f"a checker passes it: system {sorted(found['system'])}, flow {sorted(found['flow'])}"
            else:
                reason = None if found["system"] == found["flow"] else f"system says {sorted(found['system'])}, flow {sorted(found['flow'])}"
            print(f"FAIL {name}: {reason}" if reason else f"PASS {name}")
            failed |= bool(reason)
    worded = {skill: rules(skill) for skill in FIXTURES}
    apart = [rule for rule in RULES if not worded["system"].get(rule) or worded["system"].get(rule) != worded["flow"].get(rule)]
    print(f"FAIL rules: {', '.join(apart)} worded apart or missing" if apart else "PASS rules")
    failed |= bool(apart)
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

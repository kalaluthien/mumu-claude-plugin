#!/usr/bin/env python3
"""Replay the prose checks of `../contract_prose.py` on a contract of a shape no skill uses, and on system's checker through a copy of the plugin, and fail on a fault missed or a break too many.

usage: replay-prose-checks.py

prose checks: a stand-in contract of actors and calls gets one fault per check written into a copy, each in one call's note or one actor's
name; the module must return one break of the rule system names it by, at that text's place, and none for the contract as written.
system reach: on a copy of the plugin whose module checks no Korean sentence ending, system's checker must accept a description closing
outside `니다`, which it refuses on this checkout. It prints `PASS <step>` or `FAIL <step>: <reason>` per step, then PASS or FAIL."""
import copy
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

LIB = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIB))
from contract_prose import text_breaks, wording_breaks  # noqa: E402

PLUGIN = LIB.parent
CONTRACT = {
    "title": "Order lookup",
    "actors": [{"id": "shop", "name": "Shop front"}, {"id": "store", "name": "Order store"}],
    "calls": [{"id": "ask", "from": "shop", "to": "store", "name": "look up an order", "note": "sends the order number to {store}"},
              {"id": "answer", "from": "store", "to": "shop", "name": "return the order", "note": "{store}은(는) 주문을 찾아 돌려줍니다."}],
    "terms": [{"term": "order", "meaning": "what a buyer asked for", "avoid": ["purchase"]}],
}
FAULTS = [  # the text a fault replaces, by the call or actor it sits on, and the rule system names it by
    ("calls/ask/note", "costs $\\foo x$ per call", "formula"),
    ("calls/ask/note", "sends an `open quote", "text-plain"),
    ("calls/ask/note", "sends the number to {nobody}", "text-plain"),
    ("calls/ask/note", "sends <b>the number</b>", "text-plain"),
    ("calls/ask/note", "draws the call in #ff0000", "text-plain"),
    ("calls/ask/note", "asks the Order store for the number", "text-plain"),
    ("actors/store/name", "주문 창고", "name-english"),
    ("calls/answer/note", "{store}는 주문을 찾아 돌려줍니다.", "korean-text"),
    ("calls/answer/note", "{store}은(는) 주문을 찾아 돌려준다.", "korean-text"),
    ("calls/answer/note", "`order` 를 찾아 돌려줍니다.", "korean-text"),
    ("calls/ask/note", "sends the purchase number", "term-words"),
]


def breaks(contract):
    """The prose breaks of a stand-in CONTRACT, its texts and names gathered as the module asks."""
    actors, calls = contract["actors"], contract["calls"]
    names = [("title", contract["title"])] + [(f"actors/{actor['id']}/name", actor["name"]) for actor in actors]
    said = [(f"calls/{call['id']}/name", call["name"]) for call in calls] + [(f"calls/{call['id']}/note", call["note"]) for call in calls]
    said += [(f"terms/{k + 1}/meaning", entry["meaning"]) for k, entry in enumerate(contract["terms"])]
    labels = {actor["id"]: actor["name"] for actor in actors} | {call["id"]: call["name"] for call in calls}
    return text_breaks(names + said, labels) + wording_breaks(said, names, [(actor["id"], actor["name"]) for actor in actors], contract["terms"])


def written(contract, where, text):
    """A copy of CONTRACT with TEXT at WHERE, a `<list>/<id>/<field>` place."""
    changed = copy.deepcopy(contract)
    group, name, field = where.split("/")
    next(one for one in changed[group] if one["id"] == name)[field] = text
    return changed


def prose_checks():
    """Each reason the module misses a fault or breaks the contract as written."""
    found = [f"the contract as written breaks {rule} at {where}" for where, rule, _ in breaks(CONTRACT)]
    for where, text, rule in FAULTS:
        got = [(place, kind) for place, kind, _ in breaks(written(CONTRACT, where, text))]
        if got != [(where, rule)]:
            found.append(f"`{text}` at {where} gave {got or 'no break'}, expected one {rule} there")
    return found


def system_reach():
    """Each reason system's checker does not take its Korean ending check from the module."""
    contract = json.loads((PLUGIN / "skills" / "system" / "examples" / "self" / "contract.json").read_text())
    contract["purpose"] = "계약 하나로 시스템을 다시 만든다."
    with tempfile.TemporaryDirectory() as scratch:
        copied = pathlib.Path(scratch) / "paperwork"
        shutil.copytree(PLUGIN, copied, ignore=shutil.ignore_patterns("examples", "__pycache__"))
        module = copied / "lib" / "contract_prose.py"
        source = module.read_text()
        if "ENDING.findall(bare)" not in source:
            return ["the module holds no Korean ending check to drop"]
        module.write_text(source.replace("ENDING.findall(bare)", "()"))
        target = pathlib.Path(scratch) / "contract.json"
        target.write_text(json.dumps(contract, ensure_ascii=False))
        rules = [[line.split(": ")[1] for line in subprocess.run([sys.executable, str(root / "skills" / "system" / "scripts" / "check-contract.py"), "check", str(target)],
                                                                 capture_output=True, text=True).stdout.splitlines() if ": " in line] for root in (PLUGIN, copied)]
    found = [] if rules[0] == ["korean-text"] else [f"this checkout's checker gave {rules[0] or 'no break'}, expected one korean-text"]
    return found + ([] if rules[1] == [] else [f"the copy whose module checks no ending gave {rules[1]}, expected no break"])


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    failed = False
    for step, run in (("prose checks", prose_checks), ("system reach", system_reach)):
        reasons = run()
        failed = failed or bool(reasons)
        print(f"FAIL {step}: {'; '.join(reasons)}" if reasons else f"PASS {step}")
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

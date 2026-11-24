#!/usr/bin/env python3
"""Replay the prose checks of `../contract_prose.py` on a contract of a shape no skill uses, and on system's checker through a copy of the plugin, and fail on a fault missed or a break too many.

usage: replay-prose-checks.py

prose checks: a stand-in contract of actors and calls gets one fault per check written into a copy, each in one call's note or label or one
actor's name; the module must return one break of the rule system names it by, at that text's place, whose message quotes the text and names
what in it broke the rule, and none for the contract as written.
system reach: system's checker must print, line for line, what it printed before lib held its prose checks for each fault
`system-prose-breaks.json` plants in the self example; and on a copy of the plugin whose module drops one check, the Korean sentence
ending or the drawing value, it must accept a purpose that breaks it, which it refuses on this checkout. It prints `PASS <step>` or `FAIL <step>: <reason>` per step, then PASS or FAIL."""
import concurrent.futures
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
HERE = pathlib.Path(__file__).resolve().parent
SELF = PLUGIN / "skills" / "system" / "examples" / "self" / "contract.json"
CONTRACT = {
    "title": "Order lookup",
    "actors": [{"id": "shop", "name": "Shop front"}, {"id": "store", "name": "Order store"}],
    "calls": [{"id": "ask", "from": "shop", "to": "store", "label": "look up an order", "note": "sends the order number to {store}"},
              {"id": "answer", "from": "store", "to": "shop", "label": "return the order", "note": "{store}은(는) 주문을 찾아 돌려줍니다."}],
    "terms": [{"term": "order", "meaning": "what a buyer asked for", "avoid": ["purchase", "buy", "buy order"]}],
}
FAULTS = [  # the text a fault replaces, by the call or actor it sits on, the rule system names it by, and what its message must say besides the text
    ("calls/ask/note", "costs $\\foo x$ per call", "formula"),
    ("calls/ask/note", "sends an `open quote", "text-plain"),
    ("calls/ask/note", "sends a ```fence of code", "text-plain"),
    ("calls/ask/note", "sends the number to {nobody}", "text-plain"),
    ("calls/ask/note", "sends the number to <{nobody}>", "text-plain", "`{nobody}`"),
    ("calls/ask/note", "sends <b>the number</b>", "text-plain"),
    ("calls/ask/note", "sends the number as <{store}>", "text-plain", "`<Order store>`"),
    ("calls/ask/note", "draws the call in #ff0000", "text-plain"),
    ("calls/ask/note", "asks the Order store for the number", "text-plain"),
    ("calls/ask/note", "asks Order store for the number", "text-plain"),
    ("actors/store/name", "주문 창고", "name-english"),
    ("actors/store/name", "Order $x$ store", "formula"),
    ("calls/ask/label", "주문을 찾는다.", "name-english"),
    ("calls/answer/note", "{store}는 주문을 찾아 돌려줍니다.", "korean-text", "writes `는`"),
    ("calls/answer/note", "{store}은(는) 주문을 찾아 돌려준다.", "korean-text"),
    ("calls/answer/note", "`order` 를 찾아 돌려줍니다.", "korean-text"),
    ("calls/ask/note", "sends the purchase number", "term-words"),
    ("calls/ask/note", "sends the buy order number", "term-words", "says `buy order`"),
]


def breaks(contract):
    """The prose breaks of a stand-in CONTRACT, its texts and names gathered as the module asks."""
    actors, calls = contract["actors"], contract["calls"]
    names = [("title", contract["title"])] + [(f"actors/{actor['id']}/name", actor["name"]) for actor in actors]
    said = [(f"calls/{call['id']}/label", call["label"]) for call in calls] + [(f"calls/{call['id']}/note", call["note"]) for call in calls]
    said += [(f"terms/{k + 1}/meaning", entry["meaning"]) for k, entry in enumerate(contract["terms"])]
    labels = {actor["id"]: actor["name"] for actor in actors} | {call["id"]: call["label"] for call in calls}
    return text_breaks(names + said, labels) + wording_breaks(said, names, [(actor["id"], actor["name"]) for actor in actors],
                                                [(f"terms/{entry['term']}/term", entry) for entry in contract["terms"]])


def written(contract, where, text):
    """A copy of CONTRACT with TEXT at WHERE, a `<list>/<id>/<field>` place."""
    changed = copy.deepcopy(contract)
    group, name, field = where.split("/")
    next(one for one in changed[group] if one["id"] == name)[field] = text
    return changed


def prose_checks():
    """Each reason the module misses a fault or breaks the contract as written."""
    found = [f"the contract as written breaks {rule} at {where}" for where, rule, _ in breaks(CONTRACT)]
    for where, text, rule, *said in FAULTS:
        got = breaks(written(CONTRACT, where, text))
        if [(place, kind) for place, kind, _ in got] != [(where, rule)]:
            found.append(f"`{text}` at {where} gave {[(place, kind) for place, kind, _ in got] or 'no break'}, expected one {rule} there")
        elif not all(part in got[0][2] for part in [f"`{text[:40]}`", *said]):
            found.append(f"`{text}` at {where} broke {rule} saying `{got[0][2]}`, which misses {[f'`{text[:40]}`', *said]}")
    return found


REACHED = [  # a purpose system's checker refuses, the module text that makes the refusal, and what a copy writes in its place
    ("계약 하나로 시스템을 다시 만든다.", "ENDING.findall(bare)", "()"),
    ("Rebuild a system in #ff0000 from one contract.", "style = STYLE.search(", "style = None and STYLE.search("),
]


def planted(contract, sets):
    """A copy of CONTRACT with each value of SETS, a (path, value) pair, at its path, a string key in a list naming the item of that id."""
    changed = copy.deepcopy(contract)
    for path, value in sets:
        place = changed
        for key in path[:-1]:
            place = next(one for one in place if one["id"] == key) if isinstance(key, str) and isinstance(place, list) else place[key]
        place[path[-1]] = value
    return changed


def checked(contract, scratch):
    """The lines system's checker on this checkout prints for CONTRACT, its path written as `CONTRACT`."""
    target = pathlib.Path(scratch) / f"{id(contract)}.json"
    target.write_text(json.dumps(contract, ensure_ascii=False))
    lines = subprocess.run([sys.executable, str(PLUGIN / "skills" / "system" / "scripts" / "check-contract.py"), "check", str(target)],
                           capture_output=True, text=True).stdout.splitlines()
    return [line.replace(str(target), "CONTRACT") for line in lines]


def system_reach():
    """Each reason system's checker does not print what it printed before lib held its prose checks, or does not take them from lib."""
    records, contract = json.loads((HERE / "system-prose-breaks.json").read_text()), json.loads(SELF.read_text())
    with tempfile.TemporaryDirectory() as scratch, concurrent.futures.ThreadPoolExecutor(4) as pool:
        got = list(pool.map(lambda record: checked(planted(contract, record["set"]), scratch), records))
    found = [f"{record['fault']} gave {lines}, before {record['lines']}" for record, lines in zip(records, got) if lines != record["lines"]]
    for purpose, check, dropped in REACHED:
        contract = json.loads(SELF.read_text())
        contract["purpose"] = purpose
        with tempfile.TemporaryDirectory() as scratch:
            copied = pathlib.Path(scratch) / "paperwork"
            shutil.copytree(PLUGIN, copied, ignore=shutil.ignore_patterns("examples", "__pycache__"))
            module = copied / "lib" / "contract_prose.py"
            source = module.read_text()
            if check not in source:
                found.append(f"the module holds no `{check}` to drop")
                continue
            module.write_text(source.replace(check, dropped))
            target = pathlib.Path(scratch) / "contract.json"
            target.write_text(json.dumps(contract, ensure_ascii=False))
            rules = [[line.split(": ")[1] for line in subprocess.run([sys.executable, str(root / "skills" / "system" / "scripts" / "check-contract.py"), "check", str(target)],
                                                                     capture_output=True, text=True).stdout.splitlines() if ": " in line] for root in (PLUGIN, copied)]
        found += [] if rules[0] == ["korean-text" if "ENDING" in check else "text-plain"] else [f"this checkout's checker gave {rules[0] or 'no break'} on `{purpose}`"]
        found += [] if rules[1] == [] else [f"the copy without `{check}` gave {rules[1]} on `{purpose}`, expected no break"]
    return found


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

#!/usr/bin/env python3
"""Replay the prose checks of `../contract_prose.py` on a contract of a shape no skill uses, and on system's checker through a copy of the plugin, and fail on a fault missed or a break too many.

usage: replay-prose-checks.py

prose checks: a stand-in contract of actors and calls gets one fault per check written into a copy, each in one call's note or label or one
actor's name; the module must return one break of the rule system names it by, at that text's place, whose message quotes the text and names
what in it broke the rule, and none for the contract as written or with a blank name.
system reach: system's checker must print, line for line, what it printed before lib held its prose checks for each fault
`system-prose-breaks.json` plants in the self example, and lines of the digest `system-prose-fuzz.json` keeps for each contract its seed
draws from the self example, the planted texts and a few pieces; and on a copy of the plugin whose module drops one check, the Korean sentence
ending or the drawing value, it must accept a purpose that breaks it, which it refuses on this checkout. It prints `PASS <step>` or `FAIL <step>: <reason>` per step, then PASS or FAIL."""
import concurrent.futures
import copy
import hashlib
import json
import os
import pathlib
import random
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
CHECKER = PLUGIN / "skills" / "system" / "scripts" / "check-contract.py"
PIECES = ["{checker}", "{nobody}", "the Checker", "Tag catalogue", "`", "```", "<b>", "</b>", "#f00", "12px", "color: red", "$x$", "$\\foo y$",
          "는", " 를", "은(는)", "을", ".", "니다.", "다.", "계약", "명세", "box", "boxes", "validator", "-", ",", "\n", "ㅋ"]
AVOIDED = ["box", "validator", "명세", "contract", "Region", "buy order", "키 API", "edit-2"]
CONTRACT = {
    "title": "Order lookup",
    "actors": [{"id": "shop", "name": "Shop front"}, {"id": "store", "name": "Order store"}],
    "calls": [{"id": "ask", "from": "shop", "to": "store", "label": "look up an order", "note": "sends the order number to {store}"},
              {"id": "answer", "from": "store", "to": "shop", "label": "return the order", "note": "{store}은(는) 주문을 찾아 돌려줍니다."}],
    "terms": [{"id": "order", "term": "order", "meaning": "what a buyer asked for", "avoid": ["purchase", "buy", "buy order"]}],
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
    ("terms/order/avoid", ["purchase", "Order"], "term-words", "`Order` is the term `order`"),
]


def breaks(contract):
    """The prose breaks of a stand-in CONTRACT, its texts and names gathered as the module asks."""
    actors, calls = contract["actors"], contract["calls"]
    names = [("title", contract["title"])] + [(f"actors/{actor['id']}/name", actor["name"]) for actor in actors]
    said = [(f"calls/{call['id']}/label", call["label"]) for call in calls] + [(f"calls/{call['id']}/note", call["note"]) for call in calls]
    said += [(f"terms/{k + 1}/meaning", entry["meaning"]) for k, entry in enumerate(contract["terms"])]
    labels = {actor["id"]: actor["name"] for actor in actors} | {call["id"]: call["label"] for call in calls}
    return text_breaks(names + said, labels) + wording_breaks(said, names, [(actor["id"], actor["name"]) for actor in actors],
                                                [(f"terms/{entry['id']}/term", f"terms/{entry['id']}/avoid", entry) for entry in contract["terms"]])


def written(contract, where, text):
    """A copy of CONTRACT with TEXT at WHERE, a `<list>/<id>/<field>` place."""
    changed = copy.deepcopy(contract)
    group, name, field = where.split("/")
    next(one for one in changed[group] if one["id"] == name)[field] = text
    return changed


def prose_checks():
    """Each reason the module misses a fault or breaks the contract as written."""
    found = [f"the contract as written breaks {rule} at {where}" for where, rule, _ in breaks(CONTRACT)]
    blank = breaks(written(written(CONTRACT, "actors/shop/name", "  "), "calls/ask/note", "sends the (short) number to {store}"))
    found += [f"a blank name gave {[(place, kind) for place, kind, _ in blank]}, expected no break"] if blank else []
    for where, text, rule, *said in FAULTS:
        got = breaks(written(CONTRACT, where, text))
        if [(place, kind) for place, kind, _ in got] != [(where, rule)]:
            found.append(f"`{text}` at {where} gave {[(place, kind) for place, kind, _ in got] or 'no break'}, expected one {rule} there")
        elif not all(part in got[0][2] for part in [f"`{text[:40]}`" for _ in [text] if isinstance(text, str)] + said):
            found.append(f"`{text}` at {where} broke {rule} saying `{got[0][2]}`, which misses what it should say")
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


def fuzzed(contract, records, seed, count):
    """COUNT plantings, each a list of (path, value), that SEED draws: one to three text places of CONTRACT given one to three pieces of the
    texts RECORDS plant and of PIECES, and now and then a term given a word to avoid."""
    draw = random.Random(seed)
    pool = sorted({value for record in records for _, value in record["set"] if isinstance(value, str)}) + PIECES
    places = [["purpose"], ["title"]] + [["levels", level["id"], "about"] for level in contract["levels"]]
    places += [["nodes", node["id"], field] for node in contract["nodes"][:12] for field in ("label", "purpose")]
    places += [["terms", k, field] for k in range(len(contract["terms"])) for field in ("term", "meaning")]
    plantings = []
    for _ in range(count):
        sets = [[path, draw.choice(["", " "]).join(draw.choice(pool) for _ in range(draw.randint(1, 3)))] for path in draw.sample(places, draw.randint(1, 3))]
        if draw.random() < .3:
            sets.append([["terms", draw.randrange(len(contract["terms"])), "avoid"], draw.sample(AVOIDED, draw.randint(1, 2))])
        plantings.append(sets)
    return plantings


def digest(lines):
    """A short sha-256 of the LINES a checker printed."""
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()[:16]


def checked(contract, scratch, checker=CHECKER):
    """The lines CHECKER prints for CONTRACT, its path written as `CONTRACT`, with Python's hash order fixed so a set prints alike each run."""
    target = pathlib.Path(scratch) / f"{id(contract)}.json"
    target.write_text(json.dumps(contract, ensure_ascii=False))
    lines = subprocess.run([sys.executable, str(checker), "check", str(target)], capture_output=True, text=True,
                           env=os.environ | {"PYTHONHASHSEED": "0"}).stdout.splitlines()
    return [line.replace(str(target), "CONTRACT") for line in lines]


def system_reach():
    """Each reason system's checker does not print what it printed before lib held its prose checks, or does not take them from lib."""
    records, contract = json.loads((HERE / "system-prose-breaks.json").read_text()), json.loads(SELF.read_text())
    with tempfile.TemporaryDirectory() as scratch, concurrent.futures.ThreadPoolExecutor(4) as pool:
        got = list(pool.map(lambda record: checked(planted(contract, record["set"]), scratch), records))
        fuzz = json.loads((HERE / "system-prose-fuzz.json").read_text())
        plantings = fuzzed(contract, records, fuzz["seed"], len(fuzz["digests"]))
        drawn = list(pool.map(lambda sets: digest(checked(planted(contract, sets), scratch)), plantings))
    found = [f"{record['fault']} gave {lines}, before {record['lines']}" for record, lines in zip(records, got) if lines != record["lines"]]
    found += [f"fuzzed contract {n} of seed {fuzz['seed']}, planting {sets}, printed lines of digest {mine}, before {theirs}"
              for n, (sets, mine, theirs) in enumerate(zip(plantings, drawn, fuzz["digests"])) if mine != theirs]
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

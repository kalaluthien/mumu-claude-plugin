#!/usr/bin/env python3
"""Replay wording faults on every text of each example contract and of the contract with Korean descriptions, and fail when the checker misses one.

usage: replay-prose-faults.py           run both steps
usage: replay-prose-faults.py words     run the step on a term's other words
usage: replay-prose-faults.py korean    run the step on English names and Korean descriptions

words: a word a term avoids is written into every text, title and label of a copy of each `../examples/*/contract.json` and of the copy
`parcel-locker-korean`, and the checker must name the term once at each place. `check-contract.py fixtures` must print PASS, the fastest of
three runs of the checker on the larger example must take under 1 second of processor time, and `../references/contract.md` must state no rule by a bold name
that `../references/writing.md` states.

korean: the checker must refuse a Korean word in each title, label and term, accept a Korean sentence as each description, and refuse three
faults of particle and ending written into the contract with Korean descriptions. That contract's page, built by `make-page.py`, is opened
by `list-page-texts.cjs` in a headless browser, so the step needs `node`.

A step starts the checker 12 times at most, whatever the number of texts. It prints a FAIL line per fault found, then PASS or FAIL."""
import collections
import concurrent.futures
import copy
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from contract_copies import copies  # noqa: E402
from contract_levels import flat, nested  # noqa: E402
from contract_tags import catalogue  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SYSTEM = HERE.parent
CHECK = SYSTEM / "scripts" / "check-contract.py"
TAGS = catalogue(SYSTEM / "assets" / "tags.json")
KOREAN = re.compile(r"[ㄱ-ㆎ가-힣]")
NAMED = re.compile(r"\{([a-z0-9-]+)\}")
WORDS = {"English": ("passkey", "watchword", ("{}", "{}s")),
         "Korean": ("통행증", "출입증", ("{}", "{}을", "{}은", "{}으로", "{}입니다"))}
STARTS = []


def checker(call, contract, folder):
    """The lines the checker prints for CALL on CONTRACT, written into FOLDER, and its exit status."""
    STARTS.append(call)
    with tempfile.NamedTemporaryFile("w", suffix=".json", dir=folder, delete=False) as target:
        json.dump(flat(contract), target, ensure_ascii=False)
    done = subprocess.run([sys.executable, str(CHECK), call, target.name], capture_output=True, text=True)
    return done.stdout.splitlines(), done.returncode


def held(value, where):
    """Each text inside VALUE, an item of a record, as (place, holder, key): an entry of a list is named by its id, or by its count when it has none."""
    for key, part in value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else ():
        name = part["id"] if isinstance(value, list) and isinstance(part, dict) and isinstance(part.get("id"), str) else key + 1 if isinstance(value, list) else key
        if isinstance(part, str):
            yield f"{where}/{name}", value, key
        else:
            yield from held(part, f"{where}/{name}")


def texts(contract):
    """Each text of CONTRACT a writer words, as (place, holder, key, kind): kind is `name` for a title or a label, `term` for a term, `item` for
    a text of an item, and `description` for the rest. A source's own words and an item of the code form are left out."""
    def own(holder, where, names, kind):
        return [(f"{where}{name}", holder, name, kind) for name in names if isinstance(holder.get(name), str)]
    found = own(contract, "", ("title",), "name") + own(contract, "", ("purpose",), "description")
    for k, term in enumerate(contract.get("terms", [])):
        found += own(term, f"terms/{k + 1}/", ("term",), "term") + own(term, f"terms/{k + 1}/", ("meaning",), "description")
    for level in contract["levels"]:
        here = f"levels/{level['id']}/"
        found += own(level, here, ("title",), "name") + own(level, here, ("about",), "description")
        for kind in ("areas", "nodes", "edges"):
            for element in level.get(kind, []):
                place = f"{here}{kind}/{element['id']}/"
                found += own(element, place, ("label",), "name") + own(element, place, ("purpose",), "description")
                code = {item["name"] for item in TAGS[kind[:-1]].get(element["tag"], {}).get("items", []) + TAGS["common"][kind[:-1]] if item["form"] == "code"}
                found += [(where, holder, key, "item") for where, holder, key in held(element.get("info", {}), place + "info") if where[len(place) + 5:].split("/")[0] not in code]
    for scenario in contract.get("scenarios", []):
        here = f"scenarios/{scenario['id']}/"
        found += own(scenario, here, ("title",), "name") + own(scenario, here, ("purpose",), "description")
        for k, step in enumerate(scenario["steps"]):
            found += own(step, f"{here}steps/{k + 1}/", ("note",), "description")
    for item in contract.get("claims", []):
        found += own(item, f"claims/{item['id']}/", ("statement", "fault"), "description")
    for question in contract.get("questions", []):
        found += own(question, f"questions/{question['id']}/", ("asks",), "description")
    return found


def named(lines, rule):
    """The place of each line of LINES that RULE printed, with the line's message."""
    return [(line.split(f": {rule}: ")[0], line.split(f": {rule}: ")[1]) for line in lines if f": {rule}: " in line]


def differs(wanted, got, what):
    """A FAIL line for each place of WANTED the checker did not name once, and for each place it named that is not in WANTED."""
    counts = collections.Counter(got)
    faults = [f"FAIL {what}: {place} is named {counts[place]} times, not once" for place in wanted if counts[place] != 1]
    return faults + [f"FAIL {what}: {place} is named, though nothing was written there" for place in sorted(set(got) - set(wanted))]


def spoken(contract, text):
    """TEXT as a reader of a Korean description must meet it: no space, no backtick, and each `{id}` as its record's label."""
    labels = {element["id"]: element["label"] for level in contract["levels"] for kind in ("areas", "nodes", "edges") for element in level.get(kind, [])}
    return re.sub(r"[\s`]+", "", NAMED.sub(lambda match: labels.get(match.group(1), match.group(0)), text))


def naming_faults(contract, naming, drawn, what):
    """A FAIL line when DRAWN, the text WHAT shows, holds none of the texts of NAMING with its records' labels."""
    drawn = re.sub(r"\s+", "", drawn).casefold()
    return [] if any(spoken(contract, text).casefold() in drawn for _, text in naming) else [f"FAIL {what} shows no Korean description that names a record"]


def other_words(name, contract, folder, passed):
    """The faults of the words step on the contract NAME, which is checked untouched first unless it PASSED already."""
    faults = []
    lines, status = (["ok"], 0) if passed else checker("check", contract, folder)
    if status or lines != ["ok"]:
        faults.append(f"FAIL {name}: the untouched contract is refused: {lines[:1]}")
    if not contract.get("terms"):
        return faults + [f"FAIL {name}: the contract holds no term"]
    for language, (said, quoted, shapes) in WORDS.items():
        copied = copy.deepcopy(contract)
        term = copied["terms"][0]
        term["avoid"] = term.get("avoid", []) + [said, quoted]
        places = [entry for entry in texts(copied) if entry[3] != "term"]
        for k, (place, holder, key, kind) in enumerate(places):
            shape = shapes[k % len(shapes)].format(said)
            longer = quoted + ("ing" if language == "English" else "판") if k % 2 else ("over" if language == "English" else "새") + quoted
            holder[key] = f"{holder[key]} {shape.upper() if k % 3 == 2 else shape} `{quoted}` {longer}"
        lines, status = checker("check", copied, folder)
        got = named(lines, "term-words")
        what = f"{name}, {language} word"
        faults += differs([place for place, _, _, _ in places], [place for place, message in got if f"says `{said}` for the term `{term['term']}`" in message], what)
        faults += [f"FAIL {what}: {place} is refused for a word between backticks or inside a longer word" for place, message in got if f"says `{quoted}`" in message]
    return faults


def english_names(name, contract, folder):
    """The faults of the korean step on the example contract NAME."""
    copied = copy.deepcopy(contract)
    places = [entry for entry in texts(copied) if entry[3] in ("name", "term")]
    for place, holder, key, kind in places:
        holder[key] += " 이름"
    lines, status = checker("check", copied, folder)
    faults = differs([place for place, _, _, _ in places], [place for place, _ in named(lines, "name-english")], f"{name}, a Korean word in a name")
    copied = copy.deepcopy(contract)
    places = [entry for entry in texts(copied) if entry[3] == "description"]
    for k, (place, holder, key, kind) in enumerate(places):
        holder[key] = f"설명 {k + 1}을 한국어로 씁니다."
    lines, status = checker("check", copied, folder)
    described = {place for place, _, _, _ in places}
    refused = [line for line in lines if line.split(": ")[0] in described or ": name-english: " in line or ": korean-text: " in line]
    return faults + [f"FAIL {name}, a Korean sentence as each description: {line[:160]}" for line in refused]


def korean_descriptions(contract, folder):
    """The faults of the korean step on the contract with Korean descriptions: the checker, its `read` call and the page."""
    faults = []
    lines, status = checker("check", contract, folder)
    if status or lines != ["ok"]:
        faults.append(f"FAIL the contract with Korean descriptions is refused: {lines[:1]}")
    naming = [(place, holder[key]) for place, holder, key, kind in texts(contract) if kind == "description" and KOREAN.search(holder[key]) and NAMED.search(holder[key])]
    faults += naming_faults(contract, naming, "".join(checker("read", contract, folder)[0]), "read")
    faults += [f"FAIL the catalogue names {name} in Korean" for kind in ("node", "edge", "area") for tag, entry in TAGS[kind].items()
               for name in [tag] + [item["label"] for item in entry["items"] + TAGS["common"][kind]] if KOREAN.search(name)]
    copied = copy.deepcopy(contract)
    purposes = [(place, holder, key) for place, holder, key, kind in texts(copied) if kind == "description" and place.endswith("/purpose") and "/nodes/" in place]
    node = purposes[0][0].split("/")[3]
    wrong = {"after a name": f"{{{node}}}가 소포를 보관합니다.", "outside `니다`": "소포를 보관한다.", "a space before a particle": f"{{{node}}} 의 소포를 보관합니다."}
    for (place, holder, key), text in zip(purposes, wrong.values()):
        holder[key] = text
    got = named(checker("check", copied, folder)[0], "korean-text")
    if len(purposes) < len(wrong):
        faults.append("FAIL the contract with Korean descriptions holds fewer than three nodes with a purpose")
    for (place, _, _), fault in zip(purposes, wrong):
        if not any(where == place and fault in message for where, message in got):
            faults.append(f"FAIL the checker does not refuse {fault} at {place}")
    faults += [f"FAIL the checker refuses {where}, though no fault was written there" for where in sorted({where for where, _ in got} - {place for place, _, _ in purposes[:3]})]

    built = pathlib.Path(folder) / "page.html"
    source = pathlib.Path(folder) / "korean.json"
    source.write_text(json.dumps(flat(contract), ensure_ascii=False))
    STARTS.append("make-page.py")
    made = subprocess.run([sys.executable, str(SYSTEM / "scripts" / "make-page.py"), str(source), str(built)], capture_output=True, text=True)
    if made.returncode:
        return faults + [f"FAIL make-page.py builds no page: {made.stdout.splitlines()[:1]}"]
    opened = subprocess.run(["node", str(HERE / "list-page-texts.cjs"), str(built)], capture_output=True, text=True)
    if opened.returncode:
        return faults + [f"FAIL the page does not open: {(opened.stdout + opened.stderr).splitlines()[:1]}"]
    views = [json.loads(line) for line in opened.stdout.splitlines()]
    described = sorted({spoken(contract, holder[key]) for _, holder, key, kind in texts(contract) if kind in ("description", "item")}, key=len, reverse=True)
    for view in views:
        if not view["shown"]:
            faults.append(f"FAIL the page does not show {view['view']}")
        rest = re.sub(r"\s+", "", view["text"])
        for text in described:
            rest = rest.replace(text, " ")
        if KOREAN.search(rest):
            faults.append(f"FAIL the page shows Korean outside a description at {view['view']}: {''.join(KOREAN.findall(rest))[:40]}")
    return faults + naming_faults(contract, naming, "".join(view["text"] for view in views), "the page")


def main(args):
    if len(args) > 1 or args and args[0] not in ("words", "korean"):
        print(__doc__, file=sys.stderr)
        return 2
    examples = {path.parent.name: path for path in sorted((SYSTEM / "examples").glob("*/contract.json"))}
    korean = nested(dict(copies(HERE))["parcel-locker-korean"])
    faults = []
    with tempfile.TemporaryDirectory() as folder, concurrent.futures.ThreadPoolExecutor(8) as pool:
        if args != ["korean"]:
            del STARTS[:]
            larger = max(examples.values(), key=lambda path: path.stat().st_size)
            spent = []
            for _ in range(3):
                STARTS.append("check")
                before = os.times()  # the wall clock stretches with the machine's load, the checker's own processor time does not
                done = subprocess.run([sys.executable, str(CHECK), "check", str(larger)], capture_output=True, text=True)
                after = os.times()
                spent.append(after.children_user + after.children_system - before.children_user - before.children_system)
            if done.stdout.splitlines() != ["ok"]:
                faults.append(f"FAIL {larger.parent.name}: the untouched contract is refused: {done.stdout.splitlines()[:1]}")
            if min(spent) >= 1:
                faults.append(f"FAIL the checker takes {min(spent):.2f} seconds of processor time on {larger.parent.name}, 1 second or more")
            STARTS.append("fixtures")
            kept = subprocess.run([sys.executable, str(CHECK), "fixtures"], capture_output=True, text=True).stdout.splitlines()
            faults += [f"FAIL check-contract.py fixtures: {line}" for line in kept[:-1]] + ([] if kept[-1:] == ["PASS"] else ["FAIL check-contract.py fixtures does not print PASS"])
            contracts = [(name, nested(json.loads(path.read_text()))) for name, path in examples.items()] + [("parcel-locker-korean", korean)]
            faults += [fault for found in pool.map(lambda pair: other_words(*pair, folder, pair[0] == larger.parent.name), contracts) for fault in found]
            bold = [set(re.findall(r"^- \*\*([^*]+)\*\*", (SYSTEM / "references" / name).read_text(), re.MULTILINE)) for name in ("contract.md", "writing.md")]
            faults += [f"FAIL contract.md and writing.md both state the rule {name}" for name in sorted(bold[0] & bold[1])] + ([] if all(bold) else ["FAIL a playbook states no rule"])
            if len(STARTS) > 12:
                faults.append(f"FAIL the words step starts the checker {len(STARTS)} times, over 12")
        if args != ["words"]:
            del STARTS[:]
            jobs = [pool.submit(english_names, name, nested(json.loads(path.read_text())), folder) for name, path in examples.items()] + [pool.submit(korean_descriptions, korean, folder)]
            faults += [fault for job in jobs for fault in job.result()]
            if len(STARTS) > 12:
                faults.append(f"FAIL the korean step starts the checker {len(STARTS)} times, over 12")
    print("\n".join(faults + ["FAIL" if faults else "PASS"]))
    return 1 if faults else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

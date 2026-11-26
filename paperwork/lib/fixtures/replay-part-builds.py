#!/usr/bin/env python3
"""Replay a session's edit of one middle level of a system and a flow contract, and fuzz the check by part against the whole check.

usage: replay-part-builds.py [--seed N]

edit: the self example of system and the name-lookup fixture of flow, each split into part files by `check-contract.py split`, are
built by `make-page.py`, which checks and builds every part; built again with no edit, it checks and builds none; after an edit to
the `about` of the middle part, a level, which no other part reads, it checks and builds that level alone, and the page equals a
build with no earlier page; an edit to the `purpose` of a record of that level, which the top's rules read, checks and builds that
level and the top alone; a record given an alias another level holds, or the id of a scenario, property or question, is refused with
the breaks of a whole check, as is a record of each level given an id that holds spaces, and that level renamed to an id led by a
number or to a word the top's lists are named by, with a break in its `about`; with its formulas taken out, the page holds the data
blocks a whole build draws; an edit that breaks that level is refused with its break; a build
by a copy of the plugin checks and builds every part again after a change to each kind of file its key covers, the checker, the
builder, the tag catalogue and each lib module, and after an edit to that level runs the checker on that part alone, and with no edit not at all;
a check of a part the contract lacks is refused by name. Every page a build writes holds the data blocks a build of the contract
whole draws, made here from the lib functions the builder calls, with no part.
parts: every fixture contract of both skills, the break copies included, each as written and with its held lists reversed, gives by
`check --part`, once per part, with `--root`, the breaks the whole check with `--root` gives, which exits 0 or 1 with no traceback, as a
multiset of lines; as written, where its parts
join back to it, its parts checked one call each give those breaks between them, each break once, or, where two records share an id so
that a break's place reads two ways, none more often than the whole check does and every one of them.
fuzz: on each contract the checkers pass, seeded random edits of one part each, such as a text emptied, a word added, a record named,
an id or a label changed, a text led by a number or made a word the top's lists are named by, or a record dropped, build over the unedited contract's page; each build prints the breaks the whole check of
the edited contract gives, or, when there are none, writes the page a build with no earlier page writes and a build of the contract
whole draws. --seed sets the seed, 1518 by
default; a miss prints the seed, the part and the edit.
It prints `PASS <step>` or `FAIL <step>: <reason>` per step, then PASS or FAIL."""
import collections
import concurrent.futures
import copy
import functools
import json
import operator
import pathlib
import random
import re
import shutil
import subprocess
import sys
import tempfile

LIB = pathlib.Path(__file__).resolve().parents[1]
PLUGIN = LIB.parent
sys.path.insert(0, str(LIB))
from contract_copies import copies  # noqa: E402
from contract_levels import nested  # noqa: E402
from contract_parts import FLOW, SYSTEM, TOP, TOP_WORDS, join, load, split  # noqa: E402
from contract_tags import catalogue  # noqa: E402
from flow_order import before, critical, ranks  # noqa: E402
from page_parts import earlier  # noqa: E402
from tex_mathml import drawn  # noqa: E402

SKILLS = {"system": SYSTEM, "flow": FLOW}
EDITS = 12  # per contract; each costs three runs of a script
FLAGS = {"--seed"}


def run(skill, script, *args, plugin=PLUGIN):
    done = subprocess.run([sys.executable, str(plugin / "skills" / skill / "scripts" / script), *map(str, args)], capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


def lines(text):
    return collections.Counter(line for line in text.splitlines() if line and line != "ok")


def whole(skill, contract):
    """The data blocks a build of CONTRACT draws from the contract, made from it whole."""
    blocks = {"data": nested(contract) if skill == "system" else contract,
              "tags": catalogue(PLUGIN / "skills" / skill / "assets/tags.json"), "formulas": drawn(contract)}
    if skill == "flow":
        blocks["order"] = {level["id"]: {"ranks": ranks(before(contract, level)),
                                         "critical": critical(before(contract, level), {task["id"] for task in contract.get("tasks", []) if task["level"] == level["id"]})}
                           for level in contract["levels"] if level["kind"] == "plan"}
    return json.loads(json.dumps(blocks, ensure_ascii=False))


def drawn_whole(skill, contract, page):
    """Whether the page at PAGE holds the data blocks a build of CONTRACT whole draws."""
    shown = earlier(page)
    return all(name in shown and shown[name] == value for name, value in whole(skill, contract).items())


def write(file, value):
    file.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def edit_step(folder):
    found = []
    for skill, source in (("system", PLUGIN / "skills/system/examples/self/contract.json"), ("flow", PLUGIN / "skills/flow/fixtures/name-lookup.json")):
        parts_folder, page, fresh = folder / skill / "contract", folder / skill / "page.html", folder / skill / "fresh.html"
        status, _, said = run(skill, "check-contract.py", "split", source, parts_folder)
        if status:
            return [f"{skill}: split refused: {said.strip()}"]
        status, first, said = run(skill, "make-page.py", parts_folder, page)
        everything = [name for name in split(json.loads(source.read_text()), SKILLS[skill])]
        if status or f"checked and built: {', '.join(everything)}" not in first:
            found.append(f"{skill}: the first build did not check and build every part: {first}{said}".strip())
        if not drawn_whole(skill, json.loads(source.read_text()), page):
            found.append(f"{skill}: the first build's page holds other data than a build of the contract whole draws")
        status, again, said = run(skill, "make-page.py", parts_folder, page)
        if status or "checked and built: none" not in again:
            found.append(f"{skill}: a build with no edit checked or built a part: {again}{said}".strip())
        name = everything[len(everything) // 2]
        file = parts_folder / f"{name}.json"
        held = json.loads(file.read_text())
        held["about"] = held["about"].rstrip(".") + ", told again in other words."
        write(file, held)
        status, edited, said = run(skill, "make-page.py", parts_folder, page)
        others = ", ".join(other for other in everything if other != name)
        if status or f"checked and built: {name}\nkept from the earlier page: {others}\n" not in edited:
            found.append(f"{skill}: after an edit to {name} the build did not check and build it alone and keep {others}: {edited}{said}".strip())
        status, _, said = run(skill, "make-page.py", parts_folder, fresh)
        if status or page.read_bytes() != fresh.read_bytes():
            found.append(f"{skill}: the page built over the earlier one differs from one built with no earlier page {said}".strip())
        if not drawn_whole(skill, load(parts_folder, SKILLS[skill]), page):
            found.append(f"{skill}: after an edit to {name} the page holds other data than a build of the contract whole draws")
        purposed = next((record for kind in SKILLS[skill]["held"] for record in held.get(kind, []) if isinstance(record.get("purpose"), str)), None)
        if purposed:
            purposed["purpose"] = purposed["purpose"].rstrip(".") + ", said again."
            write(file, held)
            status, rebuilt, said = run(skill, "make-page.py", parts_folder, page)
            kept = ", ".join(other for other in everything if other not in (TOP, name))
            if status or f"checked and built: {TOP}, {name}\nkept from the earlier page: {kept}\n" not in rebuilt:
                found.append(f"{skill}: after an edit to the purpose of `{purposed['id']}` the build did not check and build {name} and the top alone: {rebuilt}{said}".strip())
        found += aliased(skill, parts_folder, page) + spaced(skill, parts_folder, page) + renamed(skill, parts_folder, page, name)
        if FORMULA.search(file.read_text()):
            write(file, plain(held))
            status, _, said = run(skill, "make-page.py", parts_folder, page)
            if status or not drawn_whole(skill, load(parts_folder, SKILLS[skill]), page):
                found.append(f"{skill}: after the formulas of {name} were taken out the page holds other data than a build of the contract whole draws {said}".strip())
            write(file, held)
        copy = folder / skill / "plugin"
        shutil.copytree(PLUGIN, copy, ignore=shutil.ignore_patterns("examples", "__pycache__"))
        for code in (f"skills/{skill}/scripts/check-contract.py", f"skills/{skill}/scripts/make-page.py", f"skills/{skill}/assets/tags.json", "lib/tags.json",
                     *sorted(f"lib/{file.name}" for file in (PLUGIN / "lib").glob("*.py"))):
            with open(copy / code, "a") as marked:
                marked.write("\n")  # a blank line, which leaves the code's meaning and JSON as they were
            status, recoded, said = run(skill, "make-page.py", parts_folder, page, plugin=copy)
            if status or f"checked and built: {', '.join(everything)}\n" not in recoded:
                found.append(f"{skill}: a build after a change to {code} did not check and build every part again: {recoded}{said}".strip())
        log, checker = folder / skill / "calls.log", copy / "skills" / skill / "scripts" / "check-contract.py"
        checker.write_text(f"import json, sys; open({str(log)!r}, 'a').write(json.dumps(sys.argv[1:]) + '\\n')\n" + checker.read_text())
        run(skill, "make-page.py", parts_folder, page, plugin=copy)
        held["about"] += " Once more."
        write(file, held)
        log.write_text("")
        status, _, said = run(skill, "make-page.py", parts_folder, page, plugin=copy)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        if status or calls != [["check", str(parts_folder), "--part", name]]:
            found.append(f"{skill}: after an edit to {name} the build ran the checker as {calls}, not on {name} alone {said}".strip())
        log.write_text("")
        status, _, said = run(skill, "make-page.py", parts_folder, page, plugin=copy)
        if status or log.read_text():
            found.append(f"{skill}: a build with no edit ran the checker as {log.read_text().strip()} {said}".strip())
        status, _, said = run(skill, "check-contract.py", "check", source, "--part", "levels/no-such-level")
        if status != 1 or "levels/no-such-level" not in said:
            found.append(f"{skill}: a check of a part the contract lacks was not refused by name: {said.strip()}")
        held["about"] = "Read {no-such-record} first."
        write(file, held)
        status, out, said = run(skill, "make-page.py", parts_folder, page)
        if status != 1 or "no-such-record" not in said or f"checked and built: {name}" in out:
            found.append(f"{skill}: an edit that breaks {name} was not refused with its break: {out}{said}".strip())
    return found


def aliased(skill, folder, page):
    """Why a build of FOLDER over PAGE, with a record of one level given an alias a record of another level holds, or one given the id
    of a scenario, property or question, was not refused with the breaks of a whole check, or nothing; FOLDER is left as it was."""
    levels = sorted((folder / "levels").glob("*.json"))
    held = [(file, kind, alias) for file in levels for kind in SKILLS[skill]["held"] for record in json.loads(file.read_text()).get(kind, [])
            for alias in record.get("aliases", [])]
    if not held:
        return []
    owner, kind, alias = held[0]
    top = json.loads((folder / "top.json").read_text())
    named = next(record["id"] for shared in ("scenarios", "properties", "questions") for record in top.get(shared, []))
    other = next(file for file in levels if file != owner and json.loads(file.read_text()).get(kind))
    found = []
    for file, word in ((other, alias), (owner, named)):
        text = file.read_text()
        part = json.loads(text)
        record = part[kind][0]
        record["aliases"] = [*record.get("aliases", []), word]
        write(file, part)
        missed = refused_whole(skill, folder, page)
        file.write_text(text)
        if missed:
            found.append(f"{skill}: the alias `{word}` given to `{record['id']}` in {file.name}: {missed}")
    return found


def spaced(skill, folder, page):
    """Why a build of FOLDER over PAGE, with a record of one level given its label as its id, an id holding spaces that names no part,
    was not refused with the breaks of a whole check, or nothing, for each level, a record with an `info` first; FOLDER is left as it
    was."""
    found = []
    for level in json.loads((folder / "top.json").read_text())["levels"]:
        file = folder / "levels" / f"{level}.json"
        text = file.read_text()
        part = json.loads(text)
        labelled = [record for kind in SKILLS[skill]["held"] for record in part.get(kind, []) if " " in record.get("label", "")]
        if not labelled:
            continue
        record = sorted(labelled, key=lambda record: "info" not in record)[0]
        record["id"] = record["label"]
        write(file, part)
        missed = refused_whole(skill, folder, page)
        file.write_text(text)
        found += [f"{skill}: the id `{record['id']}` in {file.name}: {missed}"] if missed else []
    return found


FORMULA = re.compile(r"\$[^$]+\$")


def plain(value):
    """VALUE with each formula in its texts written as a word."""
    if isinstance(value, dict):
        return {key: plain(entry) for key, entry in value.items()}
    if isinstance(value, list):
        return [plain(entry) for entry in value]
    return FORMULA.sub("a sum", value) if isinstance(value, str) else value


def renamed(skill, folder, page, name):
    """Why a build of FOLDER over PAGE, with level NAME renamed to an id led by a number and to a word the top's lists are named by and
    its `about` naming no record, was not refused with the breaks of a whole check, or nothing; FOLDER is left as it was."""
    level = name.removeprefix("levels/")
    found = []
    for new in (f"1-{level}", "groups"):
        copy_folder = folder.parent / f"renamed-{new}"
        shutil.rmtree(copy_folder, ignore_errors=True)
        for file in folder.rglob("*.json"):
            target = copy_folder / file.relative_to(folder)
            target = target.with_name(f"{new}.json") if target.stem == level and target.parent.name == "levels" else target
            target.parent.mkdir(parents=True, exist_ok=True)
            value = json.loads(file.read_text().replace(json.dumps(level), json.dumps(new)))
            if target.stem == new:
                value["about"] = "Read {no-such-record} first."
            write(target, value)
        missed = refused_whole(skill, copy_folder, page)
        found += [f"{skill}: level {level} renamed {new}: {missed}"] if missed else []
    return found


def refused_whole(skill, folder, page):
    """Why a build of FOLDER over PAGE was not refused with the breaks a whole check of FOLDER prints, or None."""
    status, _, refused = run(skill, "make-page.py", folder, page)
    whole_status, said, _ = run(skill, "check-contract.py", "check", folder)
    if not status or not whole_status or lines(refused) - collections.Counter({refused.splitlines()[-1]: 1}) != lines(said):
        return f"the build printed {refused.strip()[:300]!r}, the whole check {said.strip()[:300]!r}"
    return None


def contracts():
    """Every fixture contract of both skills by skill and name, the system examples included."""
    for skill in SKILLS:
        yield from ((skill, name, contract) for name, contract in copies(PLUGIN / "skills" / skill / "fixtures"))
    for example in sorted((PLUGIN / "skills/system/examples").iterdir()):
        yield "system", f"example-{example.name}", json.loads((example / "contract.json").read_text())


def reordered():
    """Each fixture contract, then each with its held lists reversed, so a break names a record at a place the parts' order does not
    keep."""
    for skill, name, contract in contracts():
        yield skill, name, contract
        if isinstance(contract, dict) and any(isinstance(contract.get(kind), list) and len(contract[kind]) > 1 for kind in SKILLS[skill]["held"]):
            yield skill, f"{name}-reversed", {key: value[::-1] if key in SKILLS[skill]["held"] and isinstance(value, list) else value for key, value in contract.items()}


def parts_step(folder):
    def compare(entry):
        k, (skill, name, contract) = entry
        file = folder / f"{k}.json"
        file.write_text(json.dumps(contract, ensure_ascii=False))
        try:
            names = list(split(contract, SKILLS[skill]))
        except ValueError:
            return None if run(skill, "check-contract.py", "check", file)[0] == 1 else f"{skill} {name}: no part holds a break, yet the whole check passes"
        root = PLUGIN / "skills" / skill
        status, said, told = run(skill, "check-contract.py", "check", file, "--root", root)
        if status not in (0, 1) or "Traceback" in said + told:
            return f"{skill} {name}: the whole check with --root did not run: exit {status}, {(said + told).strip()[:200]}"
        whole = lines(said)
        by_part = lines(run(skill, "check-contract.py", "check", file, *[word for part in names for word in ("--part", part)], "--root", root)[1])
        if whole != by_part:
            return f"{skill} {name}: the parts' checks give {sorted((by_part - whole).elements())[:2]} beyond and miss {sorted((whole - by_part).elements())[:2]}"
        if name.endswith("-reversed") or join(split(contract, SKILLS[skill]), SKILLS[skill]) != contract:
            return None
        alone = [lines(run(skill, "check-contract.py", "check", file, "--part", part, "--root", root)[1]) for part in names]
        beyond = [line for found in alone for line in (found - whole).elements()]
        missed = sorted((whole - functools.reduce(operator.or_, alone, collections.Counter())).elements())
        if not any(": unique-ids: " in line for line in whole):
            beyond, missed = sorted((sum(alone, collections.Counter()) - whole).elements()), sorted((whole - sum(alone, collections.Counter())).elements())
        return None if not beyond and not missed else f"{skill} {name}: its parts checked one call each give {beyond[:2]} beyond and miss {missed[:2]}"
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        return [miss for miss in pool.map(compare, enumerate(reordered())) if miss]


def leaves(value, path=()):
    """Each place in VALUE an edit can land, as (path, value)."""
    if isinstance(value, dict):
        return [found for key, entry in value.items() for found in leaves(entry, path + (key,))]
    if isinstance(value, list):
        return [(path, value)] + [found for k, entry in enumerate(value) for found in leaves(entry, path + (k,))]
    return [(path, value)]


def edited(parts, chance):
    """A copy of PARTS with one random edit to one part, and the part and edit in words."""
    parts = copy.deepcopy(parts)
    name = chance.choice(list(parts))
    ids = sorted({value for _, value in leaves(parts) if isinstance(value, str) and value.islower() and "-" in value and " " not in value})
    labels = sorted({record["label"] for part in parts.values() for kind in part.values() if isinstance(kind, list) for record in kind
                     if isinstance(record, dict) and isinstance(record.get("label"), str)})
    path, value = chance.choice([place for place in leaves(parts[name]) if place[0] and place[0][-1] != "level" and not (name == TOP and place[0][0] == "levels")])
    holder = parts[name]
    for key in path[:-1]:
        holder = holder[key]
    if isinstance(value, list):
        if not value:
            return None
        del value[chance.randrange(len(value))]
        return parts, f"{name}: dropped an entry of {'/'.join(map(str, path))}"
    if not isinstance(value, str):
        return None
    new = chance.choice(["", value + " again", value + " {" + chance.choice(ids or ["x"]) + "}", chance.choice(labels or ["Other"]),
                         chance.choice(ids or ["x"]), value.replace(" ", "  ", 1), f"{chance.randrange(1, 4)}-{value}", chance.choice(sorted(TOP_WORDS))])
    holder[path[-1]] = new
    return parts, f"{name}: {'/'.join(map(str, path))} {value[:30]!r} -> {new[:30]!r}"


def fuzz_step(folder, seed):
    chance = random.Random(seed)
    cases = []
    for k, (skill, name, contract) in enumerate(contracts()):
        source = folder / f"{k}.json"
        source.write_text(json.dumps(contract, ensure_ascii=False))
        if run(skill, "check-contract.py", "check", source)[0]:
            continue
        parts = split(contract, SKILLS[skill])
        made = 0
        while made < EDITS:
            change = edited(parts, chance)
            if change:
                cases.append((skill, name, source, change))
                made += 1

    def replay(entry):
        n, (skill, name, source, (parts, said)) = entry
        case = folder / f"case-{n}"
        page, fresh, contract = case / "page.html", case / "fresh.html", case / "contract.json"
        case.mkdir()
        if run(skill, "make-page.py", source, page)[0]:
            return f"{skill} {name}: the unedited contract built no page", "unread"
        contract.write_text(json.dumps(join(parts, SKILLS[skill]), ensure_ascii=False))
        whole_status, whole, _ = run(skill, "check-contract.py", "check", contract)
        status, _, refused = run(skill, "make-page.py", contract, page)
        where = f"seed {seed}, {skill} {name}, {said}"
        if whole_status not in (0, 1):
            return None, "unread"
        outcome = "refused" if whole_status else "built"
        if bool(status) != bool(whole_status) or status and lines(refused) - collections.Counter({refused.splitlines()[-1]: 1}) != lines(whole):
            return f"{where}: the build over the earlier page printed {refused.strip()[:300]!r}, the whole check {whole.strip()[:300]!r}", outcome
        if not status and (run(skill, "make-page.py", contract, fresh)[0] or page.read_bytes() != fresh.read_bytes()):
            return f"{where}: the page built over the earlier one differs from one built with no earlier page", outcome
        if not status and not drawn_whole(skill, join(parts, SKILLS[skill]), page):
            return f"{where}: the page holds other data than a build of the contract whole draws", outcome
        return None, outcome
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        results = list(pool.map(replay, enumerate(cases)))
    return [miss for miss, _ in results if miss], collections.Counter(outcome for _, outcome in results)


def main(args):
    words = [arg for arg in args if arg not in FLAGS]
    if args not in ([], ["--seed", *words]) or len(words) > 1 or words and not words[0].isdigit():
        print(__doc__, file=sys.stderr)
        return 2
    seed = int(words[0]) if words else 1518
    failed = False
    with tempfile.TemporaryDirectory() as scratch:
        folder = pathlib.Path(scratch)
        for step, found in (("edit", edit_step(folder / "edit")), ("parts", parts_step(make(folder / "parts")))):
            print(f"FAIL {step}: {'; '.join(found)}" if found else f"PASS {step}")
            failed |= bool(found)
        missed, tried = fuzz_step(make(folder / "fuzz"), seed)
        counted = f"{tried['refused']} edits refused, {tried['built']} built"
        print(f"FAIL fuzz: {'; '.join(missed[:5])}" if missed else f"PASS fuzz: {counted}, each with the breaks of a whole check or the page of a build with no earlier page")
        failed |= bool(missed)
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


def make(folder):
    folder.mkdir(parents=True)
    return folder


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

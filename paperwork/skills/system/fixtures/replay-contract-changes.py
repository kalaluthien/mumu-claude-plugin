#!/usr/bin/env python3
"""Replay the six kinds of change on each example contract and count the records each one touches.

usage: replay-contract-changes.py

On a copy of each `../examples/*/contract.json` it adds a finding to one node, renames one node, moves one node that no edge or area holds to another level, moves one edge to another node, reworks one
item of a tag from a list into a text on every node that holds it, and gives one item of the catalogue a new shown name. Each change must
touch the fewest records: one, or for the rework the nodes that hold the item and the one catalogue record. After each the checker must
accept the copy and its `read` call must print every scenario step from the record the step names. A node that edges or an area hold is also moved to another level, and the checker must name each edge and area the move strands. A new name is also given to every node and area at
once, and no other label, no level, sentence, transition, rule, scenario or property line of `read`, and no text of the contract
but a name, a source's words and an item of the code form, may still spell the old one outside a quote in backticks; each text `read` prints
that names the node, a transition's event and guard included, must show the new name, with a capital where it opens the text or follows a full stop, unless it is a file name, and never the bare `{id}`.
The checker must also refuse a position, in a field or in a table cell or a tree note, a colour, markup of thirteen kinds, a made-up tag, a comment and a declaration among them, in a purpose, a step
note and a statement, markup a node's label would make, `paths` on a property that is no fact, a colour, a length, a position or a style declaration in a text's words, a step that names no record and a step note over 60 characters, must name a scenario with no step as empty, refuse one with no `steps` field without a crash, and name a faulty step note by its scenario and step; a catalogue that is no catalogue and one given beside
`--root` in either order must be read as the call says; a catalogue that gives an item the `read` or `gaps` call reads another form, in its tag or among the common items, or another name, or that
lacks a meaning, a label or an example, names an item twice, lists a form the checker does not know, gives an example that is no text, is nested too deep to read, or holds items in another shape than a list of records, must be refused; and no tag may fix an item every element of its kind holds already. It prints one
PASS or FAIL line per change, then PASS or FAIL."""
import concurrent.futures
import copy
import json
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from contract_levels import flat, nested  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
CHECK = HERE.parent / "scripts" / "check-contract.py"
TAGS = json.loads((HERE.parent / "assets" / "tags.json").read_text())


def records(contract):
    """Each record of CONTRACT by its key: a source, a term, a level's own fields, an area, a node, an edge, a scenario, a property."""
    found = {"contract": {name: contract[name] for name in ("title", "purpose")}}
    found.update({"source " + source["id"]: source for source in contract.get("sources", [])})
    found.update({"term " + term["term"]: term for term in contract.get("terms", [])})
    for level in contract["levels"]:
        found["level " + level["id"]] = {name: value for name, value in level.items() if name not in ("areas", "nodes", "edges")}
        for kind in ("areas", "nodes", "edges"):
            found.update({element["id"]: element if kind == "edges" else {**element, "level": level["id"]} for element in level.get(kind, [])})
    found.update({item["id"]: item for item in contract.get("scenarios", []) + contract.get("properties", [])})
    return found


def catalogue_records(tags):
    """Each record of the catalogue TAGS by its key: one per item of a tag or of a kind, one per tag's meaning."""
    found = {"forms": tags["forms"]}
    for kind in ("node", "edge", "area"):
        found.update({f"{kind} every {item['name']}": item for item in tags["common"][kind]})
        for tag, entry in tags[kind].items():
            found[f"{kind} {tag}"] = entry["meaning"]
            found.update({f"{kind} {tag} {item['name']}": item for item in entry["items"]})
    return found


def differing(before, after):
    """How many records differ between two sets of records."""
    return sum(1 for key in set(before) | set(after) if before.get(key) != after.get(key))


def run(call, contract, tags=None):
    """The checker's exit status and output for CALL on CONTRACT, against the catalogue TAGS when given."""
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "contract.json"
        path.write_text(json.dumps(contract if "nodes" in contract else flat(contract)))
        command = [sys.executable, str(CHECK), call, str(path)]
        if tags is not None:
            (pathlib.Path(folder) / "tags.json").write_text(json.dumps(tags))
            command += ["--tags", str(pathlib.Path(folder) / "tags.json")]
        done = subprocess.run(command, capture_output=True, text=True)
    return done.returncode, done.stdout


def steps_read(contract, tags=None):
    """Whether the checker accepts CONTRACT and `read` prints each scenario step with the label of the record it names."""
    status, text = run("read", contract, tags)
    if status:
        return False
    lines = text.splitlines()
    labels = {key: record.get("label") for key, record in records(contract).items()}
    ends = {edge["id"]: edge for level in contract["levels"] for edge in level.get("edges", [])}
    for scenario in contract.get("scenarios", []):
        start = next(i for i, line in enumerate(lines) if f" {scenario['id']}: " in line and not line.startswith(" "))
        for k, step in enumerate(scenario["steps"]):
            edge = ends.get(step["at"])
            wanted = [labels[edge["from"]], re.sub(r"\{([a-z0-9-]+)\}", lambda match: labels[match.group(1)], edge["label"]), labels[edge["to"]]] if edge else [labels[step["at"]]]
            line = lines[start + 1 + k]
            if not line.startswith(f"  {k + 1}. ") or not all(word in line for word in wanted):
                return False
    return True


def add_finding(contract):
    node = next(node for level in contract["levels"] for node in level["nodes"] if node["tag"] != "state" and "why" not in node.get("info", {}))
    node.setdefault("info", {})["why"] = "found in a later look at the sources"
    return {"contract": 1, "catalogue": 0}, None


def rename_node(contract):
    uses = {}
    for level in contract["levels"]:
        for edge in level.get("edges", []):
            for end in (edge["from"], edge["to"]):
                uses[end] = uses.get(end, 0) + 1
    name = max(sorted(uses), key=uses.get)
    node = next(node for level in contract["levels"] for node in level["nodes"] if node["id"] == name)
    node["label"] = "the part named anew"
    first = run("read", contract)[1]
    node["label"] = "the part with a second name"
    second = run("read", contract)[1]
    shown = first.count("the part named anew") >= uses[name] and first.lower().replace("the part named anew", node["label"]) == second.lower()
    planted = copy.deepcopy(contract)
    turn = next(edge for level in planted["levels"] for edge in level.get("edges", []) if edge["tag"] == "transition")
    turn["label"] = "ask {" + name + "}"
    turn.setdefault("info", {})["guard"] = "{" + name + "} agrees"
    shown = shown and "-- ask the part with a second name [The part with a second name agrees]" in run("read", planted)[1]
    return {"contract": 1, "catalogue": 0}, None if shown else "a line that shows the node does not follow its label"


def move_node(contract):
    if len(contract["levels"]) < 2:
        return {"contract": 0, "catalogue": 0}, None
    node = {"id": "part-set-apart", "label": "the part set apart", "tag": contract["levels"][0]["nodes"][0]["tag"], "purpose": "Stand on the level that asks about it."}
    contract["levels"][0]["nodes"].append(node)
    before = copy.deepcopy(contract)
    contract["levels"][0]["nodes"].remove(node)
    contract["levels"][1]["nodes"].append(node)
    moved = differing(records(before), records(contract))
    return {"contract": 1, "catalogue": 0}, None if moved == 1 and run("check", before)[0] == 0 else f"a node moved to another level touches {moved} records, or the checker refuses it where it stood"


def stranded(contract):
    """What the checker leaves unnamed when the node of the first level that most edges hold moves to the second: each edge it
    shares with a node that stays, and itself when an area holds it; with how many it had to name."""
    first, second = contract["levels"][0], contract["levels"][1]
    shared = lambda node: [edge["id"] for edge in first.get("edges", []) if node["id"] in (edge["from"], edge["to"])]
    node = max(first["nodes"], key=lambda one: (len(shared(one)), "area" in one))
    wanted = [(key, "edge-ends") for key in shared(node)] + ([(node["id"], "area-known")] if "area" in node else [])
    first["nodes"].remove(node)
    second["nodes"].append(node)
    status, text = run("check", contract)
    named = {(line.split(": ")[0].split("/")[-1], line.split(": ")[1]) for line in text.splitlines() if line.count(": ") >= 2}
    return [key for key, rule in wanted if (key, rule) not in named] + ([] if status == 1 and wanted else ["a refusal"]), len(wanted)


SPOKEN = ("level ", "  sentence:", "  transition:", "  rule:", "principle ", "scenario ", "property ", "invariant ", "fact ", "gap ", "assumption ", "constraint ", "convention ")


def worded(value, kind=None, tag=None, name=None):
    """Each text VALUE holds that says something of the subject: all but an id, a title, a term, a label of a node or an area, a source's
    words and an item of the code form."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [text for part in value for text in worded(part, kind, tag, name)]
    found = []
    for key, part in value.items() if isinstance(value, dict) else ():
        if key in ("levels", "scenarios", "properties", "terms", "steps"):
            found += worded(part)
        elif key in ("areas", "nodes", "edges"):
            found += [text for element in part for text in worded(element, key[:-1], element["tag"])]
        elif key == "info":
            forms = {item["name"]: item["form"] for item in TAGS[kind].get(tag, {}).get("items", []) + TAGS["common"][kind]}
            found += [text for item, held in part.items() if forms.get(item) != "code" for text in worded(held, name=item)]
        elif name or key in ("purpose", "about", "meaning", "note", "statement", "fault") or key == "label" and kind == "edge":
            found += worded(part, name=name or key)
    return found


def stale_names(contract):
    """The id of each node or area whose old label a spoken line of `read` or a text of the contract still spells after every one of them
    took a new label at once."""
    named = [node for level in contract["levels"] for node in level["nodes"] + level.get("areas", [])]
    old = {node["id"]: node["label"] for node in named}
    for count, node in enumerate(named):
        node["label"] = f"the part named anew {count}"
    printed = run("read", contract)[1]
    lines = [line for line in printed.splitlines() if line.startswith(SPOKEN) or line[:5].strip().rstrip(".").isdigit()]
    names = {node["id"]: node["label"] for node in named}
    bare = [re.sub("`[^`]*`", " ", line).lower() for line in lines + worded(contract)]
    unsaid = {name for text in spoken(contract) if said(text, names) not in printed for name in re.findall(r"\{([a-z0-9-]+)\}", text)}
    stale = []
    for name, label in old.items():
        spelt = r"(?<![\w-])" + r"\s+".join(re.escape(word) for word in label.lower().split()) + r"(?![\w-])"
        if any(re.search(spelt, line) for line in bare) or name in unsaid or "{" + name + "}" in printed:
            stale.append(name)
    return stale


def spoken(contract):
    """Each text the `read` call prints from a place other than the record it names."""
    texts = [contract.get("purpose")]
    for level in contract["levels"]:
        texts += [level.get("title")] + [node.get("info", {}).get("statement") for node in level["nodes"]]
        for edge in level.get("edges", []):
            texts += [edge["label"], edge.get("info", {}).get("guard"), edge.get("info", {}).get("action")]
    for scenario in contract.get("scenarios", []):
        texts += [scenario.get("title"), scenario.get("purpose")] + [step.get("note") for step in scenario["steps"]]
    for item in contract.get("properties", []):
        texts.append(item.get("statement"))
    return [text for text in texts if isinstance(text, str)]


def said(text, names):
    """TEXT as `read` must print it: each `{id}` its node's label, with a capital where it opens TEXT or follows a full stop, unless its first word is the subject's own name."""
    def name(found):
        label = names.get(found.group(1), found.group(0))
        plain = not re.search(r"[./_\d]|[a-z][A-Z]", label.split()[0])
        return label[:1].upper() + label[1:] if plain and (found.start() == 0 or text[:found.start()].endswith(". ")) else label
    return re.sub(r"\{([a-z0-9-]+)\}", name, text)


def move_edge(contract):
    named = {step["at"] for scenario in contract.get("scenarios", []) for step in scenario["steps"]}
    named |= {name for item in contract.get("properties", []) for name in item.get("on", [])}
    choices = []
    for level in contract["levels"]:
        pairs = {(edge["from"], edge["to"]) for edge in level.get("edges", [])}
        for edge in level.get("edges", []):
            if edge["tag"] == "transition":
                continue
            for node in level["nodes"]:
                if node["tag"] != "state" and node["id"] not in (edge["from"], edge["to"]) and (edge["from"], node["id"]) not in pairs:
                    choices.append((edge["id"] not in named, edge, node["id"]))
                    break
    in_paths = {key for item in contract.get("properties", []) for path in item.get("paths", []) for key in path}
    for _, edge, target in sorted((choice for choice in choices if choice[1]["id"] not in in_paths), key=lambda choice: choice[0]):
        old, edge["to"] = edge["to"], target
        if run("check", contract)[0] == 0:
            return {"contract": 1, "catalogue": 0}, None
        edge["to"] = old
    return {"contract": 1, "catalogue": 0}, "no edge can move to another node of its level"


def rework_item(contract, tags):
    holders = {}
    for level in contract["levels"]:
        for node in level["nodes"]:
            for item in tags["node"][node["tag"]]["items"]:
                if item["form"] == "list" and item["name"] in node.get("info", {}):
                    holders.setdefault((node["tag"], item["name"]), []).append(node)
    (tag, name), nodes = max(sorted(holders.items()), key=lambda entry: len(entry[1]))
    next(item for item in tags["node"][tag]["items"] if item["name"] == name)["form"] = "text"
    stale = run("check", contract, tags)[0]
    for node in nodes:
        node["info"][name] = "; ".join(node["info"][name])
    return {"contract": len(nodes), "catalogue": 1}, None if stale == 1 else "the checker accepts the old form after the catalogue changed"


def rename_item(contract, tags):
    item = next(item for entry in tags["node"].values() for item in entry["items"])
    item["label"] = item["label"] + ", renamed"
    return {"contract": 0, "catalogue": 1}, None


def refused(contract):
    """The name of each forbidden thing the checker accepts in a copy of CONTRACT."""
    def with_node(change):
        copied = copy.deepcopy(contract)
        change(copied["levels"][0]["nodes"][0])
        return copied

    def with_property(change):
        copied = copy.deepcopy(contract)
        change(next(item for item in copied["properties"] if item["kind"] != "fact"))
        return copied

    def with_step(change):
        copied = copy.deepcopy(contract)
        change(copied["scenarios"][0]["steps"][0])
        return copied

    def with_item(value):
        copied = copy.deepcopy(contract)
        for level in copied["levels"]:
            for node in level["nodes"]:
                for item in TAGS["node"][node["tag"]]["items"] + TAGS["common"]["node"]:
                    if item["form"] == value[0] and item["name"] in node.get("info", {}):
                        node["info"][item["name"]] = value[1](node["info"][item["name"]])
                        return copied
        return None

    def with_scenario(change):
        copied = copy.deepcopy(contract)
        change(copied["scenarios"][0])
        return copied

    def with_statement(change):
        copied = copy.deepcopy(contract)
        change(copied["properties"][0])
        return copied

    tries = {
        "a position": with_node(lambda node: node.update(x=10, y=20)),
        "a position in a table cell": with_item(("table", lambda table: {"columns": table["columns"], "rows": [[{"x": 10, "y": 20}] * len(table["columns"])]})),
        "a position in a tree note": with_item(("tree", lambda tree: [{"name": tree[0]["name"], "note": {"x": 10, "y": 20}}])),
        "a colour": with_node(lambda node: node.update(color="#ff0000")),
        "markup": with_node(lambda node: node.update(purpose="<b>" + node.get("purpose", "it") + "</b>")),
        "a closing tag": with_node(lambda node: node.update(purpose=node.get("purpose", "it") + "</p>")),
        "a tag with an attribute": with_step(lambda step: step.update(note="<img src=x>")),
        "a tag drawn by its name": with_step(lambda step: step.update(note="<mark>it holds")),
        "a tag of an older page": with_statement(lambda item: item.update(statement="<center>" + item["statement"])),
        "a tag no list of tags holds": with_node(lambda node: node.update(purpose="Place <big> orders.")),
        "a tag that swallows the rest": with_step(lambda step: step.update(note="a <plaintext> b")),
        "a made-up tag": with_statement(lambda item: item.update(statement="<zzz-part>" + item["statement"])),
        "a comment": with_node(lambda node: node.update(purpose="x <!-- c --> y")),
        "markup made of a node's label": with_node(lambda node: node.update(label="mark", purpose="a <{" + node["id"] + "}>x")),
        "paths on a property that is no fact": with_property(lambda item: item.update(paths=[{"any": 1}])),
        "a declaration": with_node(lambda node: node.update(purpose="<!DOCTYPE html>")),
        "a processing instruction": with_step(lambda step: step.update(note="<?xml?> it holds")),
        "a tag after a space": with_node(lambda node: node.update(purpose="< b>x")),
        "a tag left open": with_step(lambda step: step.update(note="<blink it holds")),
        "a tag in a table cell": with_item(("table", lambda table: {"columns": table["columns"], "rows": [["<b>it</b>"] * len(table["columns"])]})),
        "a step that names no record": with_step(lambda step: step.update(at="no-such-record")),
        "a step note over 60 characters": with_step(lambda step: step.update(note="x" * 61)),
        "a hex colour in a purpose": with_node(lambda node: node.update(purpose="draws itself in #ff0000")),
        "a colour function in a purpose": with_node(lambda node: node.update(purpose="draws itself in rgb(255, 0, 0)")),
        "a style declaration in a step note": with_step(lambda step: step.update(note="color: red")),
        "a position in a step note": with_step(lambda step: step.update(note="shown at x=4")),
        "a length in a purpose": with_node(lambda node: node.update(purpose="sits 10px lower")),
        "a scenario with no steps field": with_scenario(lambda scenario: scenario.pop("steps")),
    }
    empty = copy.deepcopy(contract)
    empty["scenarios"][0]["steps"] = []
    said = run("check", empty)[1]
    unnamed = ["a scenario with no step, named as empty"] if "steps: form: is empty" not in said or "steps[0]" in said else []
    kept = copy.deepcopy(contract)
    first = kept["levels"][0]["nodes"][0]
    first["label"] = "kept-name.txt"
    kept["properties"][0]["statement"] = "{" + first["id"] + "} holds it. {" + first["id"] + "} is read."
    unnamed += ["a file name shown with a capital"] if "kept-name.txt holds it. kept-name.txt is read." not in run("read", kept)[1] else []
    noted = with_step(lambda step: step.update(note="<b>it"))
    place = f"scenarios/{noted['scenarios'][0]['id']}/steps/1/note: text-plain"
    unnamed += ["a faulty step note, named by its scenario and step"] if place not in run("check", noted)[1] else []
    given = {name: copied for name, copied in tries.items() if copied is not None}
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        statuses = pool.map(lambda copied: run("check", copied)[0], given.values())
    return [name for name, status in zip(given, statuses) if status != 1] + unnamed


def misread_calls(path):
    """What the checker does wrong with a catalogue given beside `--root`, or with a file that is no catalogue."""
    faults = []
    with tempfile.TemporaryDirectory() as folder:
        whole, changed = pathlib.Path(folder) / "tags.json", copy.deepcopy(TAGS)
        holder = next((tag, item) for tag, entry in changed["node"].items() for item in entry["items"] if item["form"] == "list"
                      and any(node["tag"] == tag and item["name"] in node.get("info", {}) for node in json.loads(path.read_text())["nodes"]))
        holder[1]["form"] = "text"
        whole.write_text(json.dumps(changed))
        for order in (["--tags", str(whole), "--root", folder], ["--root", folder, "--tags", str(whole)]):
            done = subprocess.run([sys.executable, str(CHECK), "check", str(path)] + order, capture_output=True, text=True)
            if done.returncode != 1 or "info-form" not in done.stdout or "evidence-source" not in done.stdout:
                faults.append(f"`{order[0]}` before `{order[2]}` does not check against both")
        for name, text in (("no JSON", "x"), ("a list", "[]"), ("an empty object", "{}"), ("an item of an unknown form", json.dumps({**TAGS, "common": {**TAGS["common"], "node": [{"name": "why", "form": "picture"}]}})),
                           ("an item with no form", json.dumps({**TAGS, "common": {**TAGS["common"], "node": [{"name": "why"}]}})),
                           ("an item named twice", json.dumps({**TAGS, "common": {**TAGS["common"], "node": TAGS["common"]["node"] + TAGS["common"]["node"][:1]}})),
                           ("a form the checker does not know", json.dumps({**TAGS, "forms": TAGS["forms"] + ["picture"]})),
                           ("an example that is no text", json.dumps({**TAGS, "common": {**TAGS["common"], "node": [{**TAGS["common"]["node"][0], "example": 5}] + TAGS["common"]["node"][1:]}})),
                           ("nested too deep to read", "[" * 100000)):
            whole.write_text(text)
            done = subprocess.run([sys.executable, str(CHECK), "check", str(path), "--tags", str(whole)], capture_output=True, text=True)
            if done.returncode != 2 or done.stdout or "usage:" not in done.stderr:
                faults.append(f"a catalogue that is {name} is not refused as a call it cannot read")
    return faults


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    examples = sorted((HERE.parent / "examples").glob("*/contract.json"))

    def replayed(path):
        failed, lines = 0, []
        original = nested(json.loads(path.read_text()))
        for change in (add_finding, rename_node, move_node, move_edge, rework_item, rename_item):
            contract, tags = copy.deepcopy(original), copy.deepcopy(TAGS)
            wanted, fault = change(contract, tags) if change in (rework_item, rename_item) else change(contract)
            touched = {"contract": differing(records(original), records(contract)), "catalogue": differing(catalogue_records(TAGS), catalogue_records(tags))}
            if not fault and touched != wanted:
                fault = f"touched {touched['contract']} contract and {touched['catalogue']} catalogue records, expected {wanted['contract']} and {wanted['catalogue']}"
            if not fault and not steps_read(contract, tags):
                fault = "the checker refuses the copy, or a scenario step is not read from its record"
            failed += bool(fault)
            name = change.__name__.replace("_", " ")
            lines.append(f"FAIL {path.parent.name}: {name}: {fault}" if fault else f"PASS {path.parent.name}: {name}: {touched['contract']} contract and {touched['catalogue']} catalogue records")
        stale = stale_names(copy.deepcopy(original))
        failed += bool(stale)
        lines.append(f"FAIL {path.parent.name}: a spoken line still spells the old label of {', '.join(stale)}" if stale else f"PASS {path.parent.name}: no spoken line spells a node's old label")
        unnamed, held = stranded(copy.deepcopy(original)) if len(original["levels"]) > 1 else ([], 0)
        failed += bool(unnamed)
        lines.append(f"FAIL {path.parent.name}: move held node: the checker does not name {', '.join(unnamed)}" if unnamed else f"PASS {path.parent.name}: move held node: the checker names each of the {held} edges and areas the move strands")
        accepted = refused(original)
        failed += bool(accepted)
        lines.append(f"FAIL {path.parent.name}: the checker accepts {', '.join(accepted)}" if accepted else f"PASS {path.parent.name}: the checker refuses a position, a colour, markup and a bad step")
        misread = misread_calls(path)
        failed += bool(misread)
        lines.append(f"FAIL {path.parent.name}: {'; '.join(misread)}" if misread else f"PASS {path.parent.name}: the checker reads a catalogue beside a root and refuses what is no catalogue")
        return failed, lines

    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        done = list(pool.map(replayed, examples))
    failed = sum(count for count, _ in done)
    print("\n".join(line for _, lines in done for line in lines))
    twice = [f"{kind} {tag} {item['name']}" for kind in ("node", "edge", "area") for tag, entry in TAGS[kind].items() for item in entry["items"]
             if any(item["name"] == shared["name"] for shared in TAGS["common"][kind])]
    failed += bool(twice)
    print(f"FAIL the catalogue fixes twice: {', '.join(twice)}" if twice else "PASS the catalogue fixes each item in one record")
    reformed, given = [], []
    for kind in ("node", "edge", "area"):
        for tag, entry in TAGS[kind].items():
            for k, item in enumerate(entry["items"]):
                tries = []
                for form in TAGS["forms"] if item["name"] in ("statement", "guard", "action", "initial", "terminal", "ignores", "refuses") and examples else ():
                    tags, shared = copy.deepcopy(TAGS), copy.deepcopy(TAGS)
                    tags[kind][tag]["items"][k]["form"] = form
                    shared["common"][kind].append({**item, "form": form})
                    tries += [(f"as {form}", tags), (f"as {form} among the common items", shared)] if form != item["form"] else []
                if tries:
                    renamed = copy.deepcopy(TAGS)
                    renamed[kind][tag]["items"][k]["name"] = item["name"] + "-anew"
                    tries.append(("under another name", renamed))
                given += [(f"{kind} {tag} {item['name']} {how}", tags) for how, tags in tries]
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        statuses = pool.map(lambda one: run("read", json.loads(examples[0].read_text()), one[1])[0], given)
    reformed += [name for (name, _), status in zip(given, statuses) if status != 2]
    for field in ("label", "example", "meaning"):
        tags = copy.deepcopy(TAGS)
        entry = next(iter(tags["node"].values()))
        del (entry if field == "meaning" else entry["items"][0])[field]
        reformed += [f"a tag with no {field}"] if examples and run("check", json.loads(examples[0].read_text()), tags)[0] != 2 else []
    for shape, change in (("a tag whose items are no list", lambda tags: next(iter(tags["node"].values())).update(items={})),
                          ("common items that are no list", lambda tags: tags["common"].update(node={})),
                          ("an item that is no record", lambda tags: next(iter(tags["node"].values()))["items"].append("statement"))):
        tags = copy.deepcopy(TAGS)
        change(tags)
        reformed += [shape] if examples and run("check", json.loads(examples[0].read_text()), tags)[0] != 2 else []
    failed += bool(reformed)
    print(f"FAIL the checker takes a catalogue that reforms {', '.join(reformed)}" if reformed else "PASS the checker refuses a catalogue that gives an item `read` or `gaps` reads another form or name, or lacks a field a call reads")
    if not examples:
        failed += 1
        print("FAIL no example contract to replay")
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

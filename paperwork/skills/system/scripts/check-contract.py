#!/usr/bin/env python3
"""Check a system contract against its rules, and print what a reader or a writer asks of it.

usage: check-contract.py check CONTRACT.json [--root DIR]   print each break as `where: rule: message`, then `ok`, or the break
                                                            count on stderr; with --root, each source path must exist under DIR
usage: check-contract.py check CONTRACT.json --tags FILE    the same, against the tag catalogue in FILE; --root and --tags go together in
                                                            either order
usage: check-contract.py read CONTRACT.json [--tags FILE]   print each level as sentences, transitions and links to read aloud
usage: check-contract.py gaps CONTRACT.json                 print how much each extraction topic holds, then each open question
usage: check-contract.py tags                               print each tag with its meaning and the items it calls for
usage: check-contract.py catalogue                          check the tag catalogue against its reference: every tag named, 24 sources or
                                                            more cited, every tag with an item, the tags state, credential and queue, and none named requirement
usage: check-contract.py rules                              print each rule and what it asks
usage: check-contract.py fixtures                           check every contract in fixtures/, a JSON object, with the skill's folder as its root: one whose name
                                                            opens with a rule's must break that rule alone, any other must pass

Exit status 0 means ok, 1 a break or an open question, 2 a call it cannot read."""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
CATALOGUE = json.loads((HERE.parent / "assets" / "tags.json").read_text())
TAGS = CATALOGUE
KINDS = ("property", "invariant", "fact", "gap", "assumption", "constraint", "convention")
STRENGTHS = ("must", "should", "may")
STATUSES = ("holds", "broken", "unknown")
BASES = ("observed", "documented", "inferred")
REFERENCE = re.compile(r"\{([a-z0-9-]+)\}")
OWN = re.compile(r"[./_\d]|[a-z][A-Z]")
STYLE = re.compile(r"#(?:[0-9a-fA-F]{6}|(?=[0-9a-fA-F]{0,2}[a-fA-F])[0-9a-fA-F]{3})\b|\b(?:rgba?|hsla?|oklch)\(|\b\d+(?:\.\d+)?px\b|\b[xy]\s*=\s*-?\d"
                   r"|\b(?:color|background|background-color|left|top|right|bottom|width|height|margin|padding|font-size|font-family|font-weight|border|opacity|z-index)\s*:\s*\S")
MARKUP = re.compile(r"<\s*[A-Za-z/!?][^<>]{0,30}>?")
WEAK = {"a", "an", "the"}
BARE = WEAK | {"at", "by", "for", "from", "in", "of", "on", "to", "with"}
FAULTS = ("missing", "illegal", "redundant", "overloaded", "contradictory", "unknown")
RULES = {
    "form": "every part holds its required fields, each of the right type",
    "unique-ids": "an id is lowercase words and digits joined by `-`; a level, area, node, edge, scenario, property or source id is used once in the whole contract",
    "tag-known": "an area, node or edge carries a tag of its kind from the catalogue",
    "info-item": "an `info` key is an item of its element's tag, or an item every element of that kind may hold",
    "info-form": "an `info` value has the shape of its item's form: text, number, list, table, tree or code",
    "area-known": "a node's `area` is an area of its level",
    "edge-ends": "an edge joins two different nodes of its own level, one pair is joined once by one label in a direction, and the edge's id holds neither end's id",
    "edge-sentence": "a static edge's label opens in lower case, holds no full stop, question or exclamation mark, closes with no article, is more than a lone preposition and holds neither end's label; that it opens with a verb and that `<from label> <label> <to label>` is true is the writer's to check by the `read` call",
    "level-links": "`opens` names a level, every level but the first is opened by at least one node, and no chain of `opens` leads from a level back to it, so the first level is opened by none",
    "purpose-missing": "every node that is no state says its purpose",
    "state-region": "a state sits in an area tagged region, and a region holds only states",
    "region-initial": "a region's `initial` names one of its states",
    "transition-ends": "a transition joins two states of one region, only a transition joins two states, and none leaves a state marked `terminal`",
    "fact-paths": "a fact names two different paths of edges that start at one node and end at one node",
    "scenario-steps": "a step names a node or an edge by its id and adds a note of 60 characters at most that names neither end of its own edge, and one scenario at least is a principle",
    "property-form": "one invariant or property at least is stated; a property's kind, strength and status are known words, a gap alone names its fault, and each `on` names a node, an edge, an area, a level or a scenario",
    "evidence-source": "an evidence entry is a source id, `id:line` or `id:line-line`; under --root each source path that is no url exists and holds the lines cited",
    "text-plain": "a text names another record as `{id}`, which must exist, no text but a name, a source's words, an item of the code form and a quote in backticks spells the label of a node or an area: it names the record, so a rename reaches it; a label is two words or more, or the subject's own one-word name, and holds no other label; and a text holds no markup and no drawing value: outside backticks no `<` opens a word, a slash, `!` or `?`, whatever the word, and there is no hex colour, colour function, length in `px`, `x=` or `y=` number, or style declaration such as `left: 4`; an item of the code form is quoted as it is",
}
TOPICS = (
    ("components and their purpose", lambda contract: len(nodes(contract, lambda node: node.get("tag") != "state"))),
    ("relations between components", lambda contract: len(edges(contract, lambda edge: edge.get("tag") != "transition"))),
    ("layers and hierarchy", lambda contract: len(contract["levels"]) - 1),
    ("partitioning and boundaries", lambda contract: sum(len(level.get("areas", [])) for level in contract["levels"])),
    ("naming and placement conventions", lambda contract: kinds(contract, "convention")),
    ("coupling and dependency", lambda contract: len(edges(contract, lambda edge: edge.get("tag") == "dependsOn")) + kinds(contract, "fact")),
    ("system documents", lambda contract: len(contract.get("sources", []))),
    ("state", lambda contract: len(nodes(contract, lambda node: node.get("tag") in ("state", "dataStore", "queue")))),
    ("control", lambda contract: len(nodes(contract, lambda node: node.get("tag") in ("trigger", "router", "policy"))) + len(edges(contract, lambda edge: edge.get("tag") in ("transition", "triggers", "sequence", "governs")))),
    ("observation", lambda contract: items(contract, "signals")),
    ("interfaces and payloads", lambda contract: len(nodes(contract, lambda node: node.get("tag") == "endpoint")) + len(edges(contract, lambda edge: edge.get("tag") in ("call", "publish", "access") and edge.get("info")))),
    ("failure and degraded behaviour", lambda contract: items(contract, "failure") + items(contract, "errors")),
    ("scenarios and operational principles", lambda contract: len(contract.get("scenarios", []))),
    ("invariants and properties", lambda contract: kinds(contract, "invariant") + kinds(contract, "property")),
    ("assumptions and constraints", lambda contract: kinds(contract, "assumption") + kinds(contract, "constraint")),
    ("domain terms and coined words", lambda contract: len(contract.get("terms", []))),
    ("rationale", lambda contract: items(contract, "why")),
    ("deployment and environment", lambda contract: len(nodes(contract, lambda node: node.get("tag") == "host")) + sum(1 for level in contract["levels"] for area in level.get("areas", []) if area.get("tag") == "deployment")),
    ("security and trust", lambda contract: len(nodes(contract, lambda node: node.get("tag") in ("credential", "policy"))) + sum(1 for level in contract["levels"] for area in level.get("areas", []) if area.get("tag") == "trustZone")),
    ("actors and outside systems", lambda contract: len(nodes(contract, lambda node: node.get("tag") == "actor"))),
    ("gaps and open questions", lambda contract: kinds(contract, "gap")),
    ("evidence", lambda contract: sum(1 for element in elements(contract) if element.get("evidence"))),
)


def nodes(contract, keep=lambda node: True):
    return [node for level in contract["levels"] for node in level.get("nodes", []) if keep(node)]


def edges(contract, keep=lambda edge: True):
    return [edge for level in contract["levels"] for edge in level.get("edges", []) if keep(edge)]


def elements(contract):
    return nodes(contract) + edges(contract) + [area for level in contract["levels"] for area in level.get("areas", [])]


def kinds(contract, kind):
    return sum(1 for item in contract.get("properties", []) if item.get("kind") == kind)


def items(contract, name):
    return sum(1 for element in elements(contract) if name in element.get("info", {}))


def shown(text, labels):
    """TEXT with each `{id}` replaced by the label of the record it names, its first letter a capital where it opens TEXT or follows a full stop, unless its first word is the subject's own name, such as a file name."""
    def label(match):
        found = labels.get(match.group(1), match.group(0))
        plain = not OWN.search(found.split()[0]) if found.split() else False
        return found[:1].upper() + found[1:] if plain and (match.start() == 0 or text[:match.start()].endswith(". ")) else found
    return REFERENCE.sub(label, text)


def worded(contract, quoted):
    """Each text of CONTRACT that says something of the subject, and so may name a node: every text but an id, a label of a node or an area,
    the contract's title, a term, a source's own words and an item of the code form, whose identities QUOTED holds."""
    texts = [contract.get("purpose")] + [entry.get("meaning") for entry in contract.get("terms", [])]
    for level in contract["levels"]:
        texts += [level.get("title"), level.get("about")]
        for kind in ("areas", "nodes", "edges"):
            for element in level.get(kind, []):
                texts += [element.get("purpose"), element.get("label") if kind == "edges" else None] + strings(element.get("info", {}), quoted)
    for scenario in contract.get("scenarios", []):
        texts += [scenario.get("title"), scenario.get("purpose")] + [step.get("note") for step in scenario["steps"]]
    for item in contract.get("properties", []):
        texts += [item.get("statement"), item.get("fault")]
    return [text for text in texts if isinstance(text, str)]


def placed(value, skipped=(), where=""):
    """Every string VALUE holds, at any depth, but those whose identity is in SKIPPED, each as (where, text): WHERE is the way to it,
    an entry of a list named by its id, or by its count when it has none."""
    if id(value) in skipped:
        return []
    if isinstance(value, str):
        return [(where.lstrip("/") or "text", value)]
    if isinstance(value, list):
        value = {entry["id"] if isinstance(entry, dict) and isinstance(entry.get("id"), str) else k + 1: entry for k, entry in enumerate(value)}
    return [pair for key, part in value.items() for pair in placed(part, skipped, f"{where}/{key}")] if isinstance(value, dict) else []


def strings(value, skipped=()):
    """Every string VALUE holds, at any depth, but those whose identity is in SKIPPED."""
    return [text for _, text in placed(value, skipped)]


def tag_items(kind, tag):
    """The items an element of KIND with TAG may hold: its tag's own, then the ones common to the kind."""
    return {item["name"]: item for item in TAGS[kind].get(tag, {}).get("items", []) + TAGS["common"][kind]}


def fits(value, form):
    """True when VALUE has the shape FORM asks."""
    if form in ("text", "code"):
        return isinstance(value, str) and bool(value.strip())
    if form == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) or isinstance(value, str) and bool(value.strip())
    if form == "list":
        return isinstance(value, list) and bool(value) and all(isinstance(entry, str) for entry in value)
    if form == "table":
        return (isinstance(value, dict) and set(value) == {"columns", "rows"} and isinstance(value["columns"], list) and bool(value["columns"])
                and isinstance(value["rows"], list) and all(isinstance(name, str) for name in value["columns"])
                and all(isinstance(row, list) and len(row) == len(value["columns"]) and all(isinstance(cell, (str, int, float)) and not isinstance(cell, bool) for cell in row)
                        for row in value["rows"]))
    return isinstance(value, list) and bool(value) and all(
        isinstance(entry, dict) and isinstance(entry.get("name"), str) and set(entry) <= {"name", "note", "children"} and isinstance(entry.get("note", ""), str)
        and ("children" not in entry or fits(entry["children"], "tree")) for entry in value)


OPTIONAL = {"area": str, "opens": str, "purpose": str, "about": str, "note": str, "authority": str, "strength": str, "status": str, "fault": str,
            "many": bool, "principle": bool, "coined": bool, "on": list, "paths": list, "sources": list, "terms": list, "scenarios": list,
            "properties": list, "areas": list, "edges": list}


def form_breaks(contract):
    """Breaks of the `form` rule; any of them stops the other rules, which read the fields freely."""
    found = []

    def each(where, value, filled=False):
        if not isinstance(value, list):
            found.append((where, "form", "must be a list"))
        elif filled and not value:
            found.append((where, "form", "is empty; it holds one entry at least"))
        return list(enumerate(value)) if isinstance(value, list) else []

    def need(where, holder, fields, optional=()):
        if not isinstance(holder, dict):
            found.append((where, "form", "must be an object"))
            return False
        for name, kind in fields.items():
            if not isinstance(holder.get(name), kind) or kind is str and not holder[name].strip():
                found.append((where, "form", f"`{name}` is missing or no {kind.__name__}"))
        for name in set(holder) - set(fields) - set(optional):
            found.append((where, "form", f"`{name}` is no field here"))
        for name, kind in OPTIONAL.items():
            if name in holder and name in optional and not isinstance(holder[name], kind):
                found.append((where, "form", f"`{name}` must be a {kind.__name__}"))
        if isinstance(holder.get("on"), list) and not all(isinstance(name, str) for name in holder["on"]):
            found.append((where, "form", "`on` must be a list of ids"))
        for name in ("info",):
            if name in holder and not isinstance(holder[name], dict):
                found.append((where, "form", "`info` must be an object"))
        if "evidence" in holder and not (isinstance(holder["evidence"], list) and all(isinstance(entry, str) for entry in holder["evidence"])):
            found.append((where, "form", "`evidence` must be a list of strings"))
        if "basis" in holder and holder["basis"] not in BASES:
            found.append((where, "form", f"`basis` is one of {', '.join(BASES)}"))
        return True

    proof = ("info", "evidence", "basis")
    if not need("contract", contract, {"title": str, "purpose": str, "levels": list}, ("sources", "terms", "scenarios", "properties")):
        return found
    for i, source in each("sources", contract.get("sources", [])):
        need(f"sources[{i}]", source, {"id": str, "path": str, "says": str}, ("authority",))
    for i, term in each("terms", contract.get("terms", [])):
        need(f"terms[{i}]", term, {"term": str, "meaning": str}, ("coined",))
    for i, level in each("levels", contract.get("levels"), True):
        where = f"levels[{i}]"
        if not need(where, level, {"id": str, "title": str, "nodes": list}, ("about", "areas", "edges")):
            continue
        for kind, fields, optional in (("areas", {"id": str, "label": str, "tag": str}, proof),
                                       ("nodes", {"id": str, "label": str, "tag": str}, ("area", "opens", "purpose") + proof),
                                       ("edges", {"id": str, "from": str, "to": str, "label": str, "tag": str}, ("many",) + proof)):
            group = level.get(kind, [])
            for k, element in each(f"{where}.{kind}", group):
                need(f"{where}.{kind}[{k}]", element, fields, optional)
    for i, scenario in each("scenarios", contract.get("scenarios", [])):
        where = f"scenarios[{i}]"
        if need(where, scenario, {"id": str, "title": str, "purpose": str, "steps": list}, ("principle",)):
            for k, step in each(f"{where}.steps", scenario["steps"], True) if "steps" in scenario else ():
                need(f"{where}.steps[{k}]", step, {"at": str}, ("note",))
    for i, item in each("properties", contract.get("properties", [])):
        need(f"properties[{i}]", item, {"id": str, "kind": str, "statement": str}, ("strength", "status", "fault", "on", "paths", "evidence", "basis"))
    return found


def cited(entry, sources, root):
    """What is wrong with one evidence ENTRY: an unknown source, or lines the source's file does not hold."""
    name, _, lines = entry.partition(":")
    if name not in sources:
        return [f"`{entry}` opens with no source id; one of {', '.join(sources)}"]
    span = re.fullmatch(r"(\d+)(?:-(\d+))?", lines)
    if lines and not (span and 1 <= int(span.group(1)) <= int(span.group(2) or span.group(1))):
        return [f"`{entry}` must end with a line or a range of lines, such as `{name}:7` or `{name}:7-15`"]
    path = None if root is None or "://" in sources[name]["path"] else root / sources[name]["path"]
    if span and path is not None and path.is_file() and int(span.group(2) or span.group(1)) > len(path.read_text(errors="replace").splitlines()):
        return [f"`{entry}` names a line past the end of `{sources[name]['path']}`"]
    return []


def breaks(contract, root=None):
    """Every break of CONTRACT as (where, rule, message), in the order a reader meets them."""
    found = form_breaks(contract)
    if found:
        return found
    levels = {level["id"]: level for level in contract["levels"]}
    seen = {}
    named = [(f"level {level['id']}", level["id"]) for level in contract["levels"]]
    named += [(f"{level['id']}/{element['id']}", element["id"]) for level in contract["levels"] for kind in ("areas", "nodes", "edges") for element in level.get(kind, [])]
    named += [(f"source {source['id']}", source["id"]) for source in contract.get("sources", [])]
    named += [(f"{kind} {item['id']}", item["id"]) for kind in ("scenarios", "properties") for item in contract.get(kind, [])]
    for where, name in named:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            found.append((where, "unique-ids", f"`{name}` is not lowercase words joined by `-`, so no text can name it as `{{id}}`"))
        if name in seen:
            found.append((where, "unique-ids", f"`{name}` is also {seen[name]}"))
        seen.setdefault(name, where)
    sources = {source["id"]: source for source in contract.get("sources", [])}
    for source in sources.values():
        if root is not None and "://" not in source["path"] and not (root / source["path"]).exists():
            found.append((f"source {source['id']}", "evidence-source", f"`{source['path']}` is not under {root}"))
    opened = {name: [] for name in levels}
    for level in contract["levels"]:
        home = level["id"]
        area_tags = {area["id"]: area["tag"] for area in level.get("areas", [])}
        node_of = {node["id"]: node for node in level["nodes"]}
        for kind, group in (("area", level.get("areas", [])), ("node", level["nodes"]), ("edge", level.get("edges", []))):
            for element in group:
                where = f"{home}/{element['id']}"
                if element["tag"] not in TAGS[kind]:
                    found.append((where, "tag-known", f"`{element['tag']}` is no {kind} tag; one of {', '.join(TAGS[kind])}"))
                    continue
                allowed = tag_items(kind, element["tag"])
                for name, value in element.get("info", {}).items():
                    if name not in allowed:
                        found.append((where, "info-item", f"`{name}` is no item of {element['tag']}; one of {', '.join(allowed)}"))
                    elif not fits(value, allowed[name]["form"]):
                        found.append((where, "info-form", f"`{name}` must be a {allowed[name]['form']}"))
                found += [(where, "evidence-source", message) for entry in element.get("evidence", []) for message in cited(entry, sources, root)]
        for node in level["nodes"]:
            where = f"{home}/{node['id']}"
            if "area" in node and node["area"] not in area_tags:
                found.append((where, "area-known", f"`{node['area']}` is no area of this level"))
            if "opens" in node:
                if node["opens"] not in levels:
                    found.append((where, "level-links", f"`{node['opens']}` is no level"))
                else:
                    opened[node["opens"]].append(home)
            in_region = area_tags.get(node.get("area")) == "region"
            if node["tag"] == "state" and not in_region:
                found.append((where, "state-region", "a state sits in an area tagged region"))
            if node["tag"] != "state" and in_region:
                found.append((where, "state-region", "a region holds only states"))
            if node["tag"] != "state" and not str(node.get("purpose", "")).strip():
                found.append((where, "purpose-missing", "say what need this serves"))
        for area in level.get("areas", []):
            if area["tag"] == "region":
                inside = [node["id"] for node in level["nodes"] if node.get("area") == area["id"]]
                if area.get("info", {}).get("initial") not in inside:
                    found.append((f"{home}/{area['id']}", "region-initial", f"`info.initial` names one of {', '.join(inside) or 'its states'}"))
        pairs = set()
        for edge in level.get("edges", []):
            where = f"{home}/{edge['id']}"
            ends = [node_of.get(edge["from"]), node_of.get(edge["to"])]
            if None in ends or edge["from"] == edge["to"] or (edge["from"], edge["to"], edge["label"]) in pairs:
                found.append((where, "edge-ends", "an edge joins two different nodes of this level, once by one label in a direction"))
                continue
            for end in (edge["from"], edge["to"]):
                if re.search(rf"(^|-){re.escape(end)}(-|$)", edge["id"]):
                    found.append((where, "edge-ends", f"the id holds the id of its end `{end}`, so moving that end would leave the id false; name the edge for what it does"))
            pairs.add((edge["from"], edge["to"], edge["label"]))
            words, faults = edge["label"].split(), []
            if edge["tag"] != "transition":
                faults += ["opens with a capital or a mark"] if not re.match(r"[a-z]", edge["label"]) else []
                faults += [f"holds `{mark}`" for mark in sorted(set(re.findall(r"[.!?]", edge["label"])))]
                faults += [f"closes with the article `{words[-1]}`"] if words[-1:] and words[-1] in WEAK else []
                faults += ["is a lone preposition"] if len(words) == 1 and words[0] in BARE else []
                faults += [f"holds the end's label `{end['label']}`" for end in ends if end["label"] in edge["label"] or "{" + end["id"] + "}" in edge["label"]]
            if faults:
                found.append((where, "edge-sentence", f"`{edge['label']}` {', '.join(faults)}; from label, label and to label read as one sentence"))
            states = [node["tag"] == "state" for node in ends]
            if edge["tag"] == "transition" and not (all(states) and ends[0].get("area") == ends[1].get("area")):
                found.append((where, "transition-ends", "a transition joins two states of one region"))
            if edge["tag"] != "transition" and all(states):
                found.append((where, "transition-ends", "only a transition joins two states"))
            if edge["tag"] == "transition" and "terminal" in ends[0].get("info", {}):
                found.append((where, "transition-ends", "no transition leaves a state marked `terminal`"))
    first = contract["levels"][0]["id"]
    for name, openers in opened.items():
        if name != first and not openers:
            found.append((f"level {name}", "level-links", "every level but the first is opened by a node"))
    for name in levels:
        above, queue = set(), list(opened[name])
        while queue:
            opener = queue.pop()
            if opener not in above:
                above.add(opener)
                queue += opened[opener]
        if name in above:
            found.append((f"level {name}", "level-links", "a chain of `opens` leads from this level back to it"))
    places = {level["id"]: {node["id"] for node in level["nodes"]} | {edge['id'] for edge in level.get("edges", [])} for level in contract["levels"]}
    everywhere = set(levels) | {name for group in places.values() for name in group} | {area["id"] for level in contract["levels"] for area in level.get("areas", [])}
    scenarios = contract.get("scenarios", [])
    if not any(scenario.get("principle") is True for scenario in scenarios):
        found.append(("scenarios", "scenario-steps", "mark one scenario at least `principle: true`: the story that shows the purpose met"))
    for scenario in scenarios:
        for k, step in enumerate(scenario["steps"]):
            if not any(step["at"] in group for group in places.values()):
                found.append((f"scenario {scenario['id']} step {k + 1}", "scenario-steps", f"`{step['at']}` is no node or edge"))
            elif len(step.get("note", "")) > 60:
                found.append((f"scenario {scenario['id']} step {k + 1}", "scenario-steps", "a step's own note is 60 characters at most; the record it names says the rest"))
            else:
                for end in sorted({str(end) for edge in edges(contract) if edge.get("id") == step["at"] for end in (edge.get("from"), edge.get("to"))}):
                    if "{" + end + "}" in step.get("note", ""):
                        found.append((f"scenario {scenario['id']} step {k + 1}", "scenario-steps", f"the note names `{end}`, an end of its own edge; the edge says its ends, so a move of one would leave the note false"))
    if not any(item.get("kind") in ("invariant", "property") for item in contract.get("properties", [])):
        found.append(("properties", "property-form", "state one invariant or property at least: what must hold while the purpose is met"))
    known = {element.get("id") for element in elements(contract)}
    names = {element.get("id"): str(element.get("label")) for element in elements(contract)}
    quoted = {id(value) for level in contract["levels"] for kind in ("area", "node", "edge") for element in level.get(kind + "s", [])
              for name, value in element.get("info", {}).items() if tag_items(kind, element["tag"]).get(name, {}).get("form") == "code"}
    homes = {}
    for where, text in placed(contract, quoted):
        homes.setdefault(text, where)
        for name in REFERENCE.findall(text):
            if name not in known:
                found.append((where, "text-plain", f"`{{{name}}}` in `{text[:40]}` names no node, edge or area, the records a text can show by a label; quote the subject's own braces or markup in an item of the code form"))
        markup = MARKUP.search(re.sub(r"`[^`]*`", "", text)) or MARKUP.search(re.sub(r"`[^`]*`", "", shown(text, names)))
        style = STYLE.search(re.sub(r"`[^`]*`", "", text))
        if style:
            found.append((where, "text-plain", f"`{style.group(0)}` in `{text[:40]}` reads as a colour, a size or a position; the page's code decides how a thing is drawn, so say what it is, or quote the subject's own value between backticks or in an item of the code form"))
        if markup:
            found.append((where, "text-plain", f"`{markup.group(0)}` in `{text[:40]}` reads as markup; the page's code decides how a text is drawn, so write a placeholder or the subject's own markup between backticks or in an item of the code form"))
    named = [element for element in elements(contract) if isinstance(element.get("label"), str) and "from" not in element]
    for element in named:
        if len(element["label"].split()) < 2 and not OWN.search(element["label"]):
            found.append((element["id"], "text-plain", f"the label `{element['label']}` of `{element['id']}` is one common word, which no check can tell from prose; give it two words or more, or the subject's own name for it, such as a file name"))
    spelt = sorted(((r"(?<![\w-])" + r"\s+".join(re.escape(word) for word in element["label"].split()) + r"(?![\w-])", element["id"]) for element in named if element["label"].split()), key=lambda pair: -len(pair[0]))
    for pattern, name in spelt:
        for element in named:
            if element["id"] != name and re.search(pattern, element["label"], flags=re.IGNORECASE):
                found.append((element["id"], "text-plain", f"the label of `{element['id']}` spells the label of `{name}`, so a new name for `{name}` would leave it stale; give it words of its own"))
    for text in worded(contract, quoted):
        rest = re.sub(r"`[^`]*`|\{[a-z0-9-]+\}", "", text)
        for pattern, name in spelt:
            rest, count = re.subn(pattern, " ", rest, flags=re.IGNORECASE)
            if count:
                found.append((homes.get(text, "text"), "text-plain", f"`{text[:40]}` spells the label of `{name}`; name it as `{{{name}}}`, so a new name reaches this text"))
    all_edges = {edge['id']: edge for edge in edges(contract)}
    for item in contract.get("properties", []):
        where = f"property {item['id']}"
        found += [(where, "evidence-source", message) for entry in item.get("evidence", []) for message in cited(entry, sources, root)]
        if item["kind"] not in KINDS or item.get("strength", "must") not in STRENGTHS or item.get("status", "holds") not in STATUSES:
            found.append((where, "property-form", f"kind is one of {', '.join(KINDS)}; strength of {', '.join(STRENGTHS)}; status of {', '.join(STATUSES)}"))
        if item["kind"] == "gap" and item.get("fault") not in FAULTS or item["kind"] != "gap" and "fault" in item:
            found.append((where, "property-form", f"a gap, and only a gap, names its fault: one of {', '.join(FAULTS)}"))
        on = item.get("on", [])
        for name in on if isinstance(on, list) else [None]:
            if name not in everywhere and name not in {scenario["id"] for scenario in scenarios}:
                found.append((where, "property-form", f"`on` names `{name}`, which is no node, edge, area, level or scenario"))
        if item["kind"] != "fact" and "paths" in item:
            found.append((where, "property-form", "a fact alone holds `paths`"))
        if item["kind"] == "fact":
            paths = item.get("paths")
            chains = isinstance(paths, list) and len(paths) == 2 and all(
                isinstance(path, list) and path and all(isinstance(key, str) and key in all_edges for key in path)
                and all(all_edges[key]["to"] == all_edges[after]["from"] for key, after in zip(path, path[1:])) for path in paths)
            if not (chains and paths[0] != paths[1] and all_edges[paths[0][0]]["from"] == all_edges[paths[1][0]]["from"]
                    and all_edges[paths[0][-1]]["to"] == all_edges[paths[1][-1]]["to"]):
                found.append((where, "fact-paths", "`paths` holds two different chains of edge keys with one start and one end"))
    return found


def read_lines(contract):
    """The contract as lines to read aloud: a static edge as a sentence, a transition as event, guard and action, a level's links."""
    openers = {}
    for level in contract["levels"]:
        for node in level["nodes"]:
            if "opens" in node:
                openers.setdefault(node["opens"], []).append(f"{node['label']} ({level['title']})")
    labels = {element["id"]: element["label"] for element in elements(contract)}
    said = {}
    lines = [f"{contract['title']}: {shown(contract['purpose'], labels)}"]
    for level in contract["levels"]:
        label = {node["id"]: node["label"] for node in level["nodes"]}
        lines.append(f"\nlevel {level['id']}: {shown(level['title'], labels)}")
        for opener in openers.get(level["id"], []):
            lines.append(f"  opened by: {opener}")
        for node in level["nodes"]:
            if "opens" in node:
                lines.append(f"  opens: {node['label']} -> {node['opens']}")
        for area in level.get("areas", []):
            inside = [node["label"] for node in level["nodes"] if node.get("area") == area["id"]]
            if area["tag"] == "region":
                lines.append(f"  region: {area['label']} is in one of: {', '.join(inside)}; first {label.get(area.get('info', {}).get('initial'), '?')}")
            else:
                lines.append(f"  area: {area['label']} ({area['tag']}) holds {', '.join(inside)}")
        for node in level["nodes"]:
            if "statement" in node.get("info", {}):
                lines.append(f"  rule: {node['label']} says {shown(node['info']['statement'], labels)}")
        for edge in level.get("edges", []):
            info = edge.get("info", {})
            if edge["tag"] == "transition":
                guard = f" [{shown(info['guard'], labels)}]" if "guard" in info else ""
                action = f" / {shown(info['action'], labels)}" if "action" in info else ""
                said[edge["id"]] = f"{label[edge['from']]} -- {shown(edge['label'], labels)}{guard}{action} --> {label[edge['to']]}"
                lines.append(f"  transition: {said[edge['id']]}")
            else:
                said[edge["id"]] = f"{label[edge['from']]} {shown(edge['label'], labels)} {'each of ' if edge.get('many') else ''}{label[edge['to']]}."
                lines.append(f"  sentence: {said[edge['id']]}")
    for scenario in contract.get("scenarios", []):
        lines.append(f"\n{'principle' if scenario.get('principle') else 'scenario'} {scenario['id']}: {shown(scenario['title'], labels)} ({shown(scenario['purpose'], labels)})")
        for k, step in enumerate(scenario["steps"]):
            lines.append(f"  {k + 1}. {said.get(step['at'], labels.get(step['at']))}" + (f" ({shown(step['note'], labels)})" if "note" in step else ""))
    for item in contract.get("properties", []):
        lines.append(f"\n{item['kind']} {item['id']} ({item.get('strength', 'must')}, {item.get('status', 'holds')}): {shown(item['statement'], labels)}")
    return lines


def gap_lines(contract):
    """What each topic holds, then each question the contract leaves open; the questions are what `gaps` exits 1 on."""
    counts = [f"{count(contract):4d}  {topic}" for topic, count in TOPICS]
    excused = {name for item in contract.get("properties", []) if item["kind"] == "gap" for name in item.get("on", [])}
    asked = []
    for topic, count in TOPICS:
        named = any(item["kind"] == "gap" and topic in item["statement"] for item in contract.get("properties", []))
        if not count(contract) and not named:
            asked.append(f"topic: nothing holds `{topic}`: look again in the sources, or record a gap whose statement names the topic in these words and says why it has none")
    for level in contract["levels"]:
        label = {node["id"]: node["label"] for node in level["nodes"]}
        for kind, group in (("node", level["nodes"]), ("edge", level.get("edges", [])), ("area", level.get("areas", []))):
            for element in group:
                name = element["id"]
                if name in excused:
                    continue
                wanted = [item["name"] for item in TAGS[kind][element["tag"]]["items"] if item.get("key")]
                if wanted and not set(wanted) & set(element.get("info", {})):
                    asked.append(f"item: {level['id']}/{name} ({element['tag']}) says no {' or '.join(wanted)}")
                if kind != "area" and not element.get("evidence"):
                    asked.append(f"evidence: {level['id']}/{name} cites nothing that shows it")
        for area in level.get("areas", []):
            if area["tag"] != "region" or area["id"] in excused:
                continue
            states = [node for node in level["nodes"] if node.get("area") == area["id"]]
            moves = [edge for edge in level.get("edges", []) if edge["tag"] == "transition" and edge["from"] in {node["id"] for node in states}]
            events = sorted({edge["label"] for edge in moves})
            reach, queue = {area["info"]["initial"]}, [area["info"]["initial"]]
            while queue:
                here = queue.pop()
                for edge in moves:
                    if edge["from"] == here and edge["to"] not in reach:
                        reach.add(edge["to"])
                        queue.append(edge["to"])
            seen = set()
            for edge in moves:
                key = (edge["from"], edge["label"], edge.get("info", {}).get("guard"))
                if key in seen:
                    asked.append(f"state: two transitions leave {label[edge['from']]} on `{edge['label']}` under one guard; which one is taken?")
                seen.add(key)
            for node in states:
                if node["id"] in excused:
                    continue
                out = {edge["label"] for edge in moves if edge["from"] == node["id"]}
                final = "terminal" in node.get("info", {})
                if node["id"] not in reach:
                    asked.append(f"state: nothing leads to {label[node['id']]} from the first state of {area['label']}")
                if not out and not final:
                    asked.append(f"state: nothing leaves {label[node['id']]}, and it is not marked terminal")
                for event in events:
                    settled = node.get("info", {}).get("ignores", []) + node.get("info", {}).get("refuses", [])
                    if event not in out and not final and event not in settled:
                        asked.append(f"state: what happens when `{event}` comes while {area['label']} is {label[node['id']]}?")
    for level in contract["levels"]:
        for node in level["nodes"]:
            touched = any(node["id"] in (edge["from"], edge["to"]) for edge in level.get("edges", []))
            if node["tag"] != "state" and not touched and "opens" not in node and node["id"] not in excused:
                asked.append(f"means: {level['id']}/{node['id']} has a purpose and no relation that serves it")
    return counts, asked


READ = {"statement": "text", "guard": "text", "action": "text", "initial": "text", "terminal": "text", "ignores": "list", "refuses": "list"}


def catalogue(path):
    """The tag catalogue the file at PATH holds, or None when it is no catalogue: a tag lacks its meaning or its list of items, an item its name, label, form or an example in words,
    a tag names an item twice, the forms are not the six the checker knows, or an item the `read` or `gaps` call reads has another form, in a tag or among the common ones,
    or has left a tag that held it."""
    try:
        tags = json.loads(pathlib.Path(path).read_text())
        whole = tags["forms"] == CATALOGUE["forms"]
        for kind in ("node", "edge", "area"):
            entries = list(tags[kind].values()) + [{"meaning": "", "items": tags["common"][kind]}]
            items = [item for entry in entries for item in entry["items"]]
            whole = (whole and all(isinstance(entry["meaning"], str) and isinstance(entry["items"], list) for entry in entries)
                     and all(isinstance(item["name"], str) and isinstance(item["label"], str) and item["form"] in tags["forms"] and isinstance(item["example"], str) and bool(item["example"].strip())
                             and item["form"] == READ.get(item["name"], item["form"]) for item in items)
                     and all(len({item["name"] for item in entry["items"]}) == len(entry["items"]) for entry in entries)
                     and all(item["name"] in [given["name"] for given in tags[kind].get(tag, {"items": [item]})["items"]]
                             for tag, entry in CATALOGUE[kind].items() for item in entry["items"] if item["name"] in READ))
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
        return None
    return tags if whole else None


def main(args):
    global TAGS
    if args == ["tags"]:
        for kind in ("node", "edge", "area"):
            for tag, entry in TAGS[kind].items():
                print(f"{kind} {tag}: {entry['meaning']}")
                for item in entry["items"]:
                    print(f"    {item['name']} ({item['label']}{', key' if item.get('key') else ''}): {item['form']}, such as {item['example']}")
            print(f"every {kind}: " + "; ".join(f"{item['name']}: {item['form']}, such as {item['example']}" for item in TAGS["common"][kind]))
        return 0
    if args == ["catalogue"]:
        text = (HERE.parent / "references" / "tags.md").read_text()
        tags = [(kind, tag, entry) for kind in ("node", "edge", "area") for tag, entry in TAGS[kind].items()]
        wrong = [f"the reference names no `{tag}`" for _, tag, _ in tags if f"`{tag}`" not in text]
        wrong += [f"{kind} tag `{tag}` fixes no item" for kind, tag, entry in tags if not entry["items"]]
        wrong += [f"`{tag}` item `{item.get('name')}` lacks a label, a form or an example" for _, tag, entry in tags for item in entry["items"]
                  if not (item.get("name") and item.get("label") and item.get("form") in TAGS["forms"] and item.get("example"))]
        wrong += [f"node tag `{tag}` is missing" for tag in ("state", "credential", "queue") if tag not in TAGS["node"]]
        wrong += ["`requirement` is a property, never a tag"] if any(tag == "requirement" for _, tag, _ in tags) else []
        cited = len(set(re.findall(r"https?://[^\s)>`]+", text)))
        wrong += [f"the reference cites {cited} sources, fewer than 24"] if cited < 24 else []
        print("\n".join(wrong) if wrong else f"ok: {len(tags)} tags, {cited} sources")
        return 1 if wrong else 0
    if args == ["rules"]:
        for rule, asks in RULES.items():
            print(f"{rule}: {asks}")
        return 0
    if args == ["fixtures"]:
        failed = 0
        for path in sorted((HERE.parent / "fixtures").glob("*.json")):
            contract = json.loads(path.read_text())
            if isinstance(contract, list):  # another runner's rows, such as the page's search queries
                continue
            rules = {rule for _, rule, _ in breaks(contract, HERE.parent)}
            wanted = {rule for rule in RULES if path.stem == rule or path.stem.startswith(rule + "-")}
            if rules != wanted:
                failed += 1
                print(f"FAIL {path.name}: broke {', '.join(sorted(rules)) or 'nothing'}, expected {', '.join(wanted) or 'nothing'}")
        missing = sorted(set(RULES) - {path.stem for path in (HERE.parent / "fixtures").glob("*.json")})
        for rule in missing:
            print(f"FAIL no fixture breaks {rule}")
        print("FAIL" if failed or missing else "PASS")
        return 1 if failed or missing else 0
    root, unread = None, ""
    while len(args) >= 4 and args[-2] in ("--root", "--tags"):
        option, value, args = args[-2], args[-1], args[:-2]
        if option == "--root" and root is None and args[0] == "check":
            root = pathlib.Path(value)
        elif option == "--tags" and TAGS is CATALOGUE and args[0] in ("check", "read") and catalogue(value):
            TAGS = catalogue(value)
        else:
            unread = f"{value} holds no tag catalogue\n" if option == "--tags" and TAGS is CATALOGUE and args[0] in ("check", "read") else unread
            args = []
    if len(args) != 2 or args[0] not in ("check", "read", "gaps") or args[1].startswith("-"):
        print(unread + __doc__, file=sys.stderr)
        return 2
    try:
        contract = json.loads(pathlib.Path(args[1]).read_text())
        found = breaks(contract, root)
    except (OSError, ValueError, RecursionError) as e:
        print(f"{args[1]}: {e}", file=sys.stderr)
        return 1
    for where, rule, message in found:
        print(f"{where}: {rule}: {message}")
    if found:
        print(f"{len(found)} breaks; `check-contract.py rules` says what each rule asks", file=sys.stderr)
        return 1
    if args[0] == "check":
        print("ok")
        return 0
    if args[0] == "read":
        print("\n".join(read_lines(contract)))
        return 0
    counts, asked = gap_lines(contract)
    print("what each topic holds:")
    print("\n".join(counts))
    print("\n".join([f"\n{len(asked)} open questions; answer each from the sources, or record a gap property `on` the element it names:"] + asked) if asked else "\nno open question")
    return 1 if asked else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

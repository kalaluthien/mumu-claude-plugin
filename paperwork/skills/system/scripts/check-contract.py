#!/usr/bin/env python3
"""Check a system contract against its rules, and print what a reader or a writer asks of it.

usage: check-contract.py check CONTRACT.json [--root DIR]   print each break as `where: rule: message`, then `ok`, or the break
                                                            count on stderr; with --root, each source path must exist under DIR
usage: check-contract.py check CONTRACT.json --tags FILE    the same, against the tag catalogue in FILE; --root and --tags go together in
                                                            either order
usage: check-contract.py read CONTRACT.json [--tags FILE]   print each level as sentences, transitions and links to read aloud
usage: check-contract.py outline CONTRACT.json [LEVEL]       print the contract, or one level of it, as leads to read from the top: a level over its areas, an area over its nodes, a node over its items
usage: check-contract.py gaps CONTRACT.json                 print how much each extraction topic holds, then each open question
usage: check-contract.py tags                               print each tag with its meaning and the items it calls for
usage: check-contract.py rules                              print each rule and what it asks
usage: check-contract.py fixtures                           check every contract of fixtures/, a whole one or a copy `contract-copies.json` holds as changes to one, with the skill's folder as its root: one whose name
                                                            opens with a rule's must break that rule alone, any other must pass

Exit status 0 means ok, 1 a break or an open question, 2 a call it cannot read."""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from contract_copies import copies  # noqa: E402
from contract_levels import nested  # noqa: E402
from tex_mathml import SUBSET, formulas, mathml, unformulated  # noqa: E402

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
PARTICLE = (r"(?:(?:이라는|이라고|으로서|으로써|에서는|에서도|에게서|으로는|으로도|이라면|입니다|이며|이고|이나|이란|이든|으로|에서|에게|에는|에도|까지|부터|처럼|보다|라는|라고|로서|로써|로는|로도"
            r"|은|는|이|가|을|를|의|에|와|과|도|만|로|며|고|나|란|든)(?![가-힣]))?")
KOREAN = re.compile(r"[ㄱ-ㆎ가-힣]")
ARTICLE = re.compile(r"^(?:an?|the)\s+", re.IGNORECASE)
PAIRED = re.compile(r"\}(은|는|이|가|을|를|과|와|으로|로)(?![가-힣(])")
ENDING = re.compile(r"([가-힣]+)\.(?=\s|$)")
APART = re.compile(r"(?:[}`]|[A-Za-z])\s+(?:은|는|가|을|를|의|에|와|과|도|로|으로|에서|에게)(?=[\s.,]|$)")
WEAK = {"a", "an", "the"}
BARE = WEAK | {"at", "by", "for", "from", "in", "of", "on", "to", "with"}
FAULTS = ("missing", "illegal", "redundant", "overloaded", "contradictory", "unknown")
RULES = {
    "form": "every part holds its required fields, each of the right type",
    "unique-ids": "an id is lowercase words and digits joined by `-`; a level, area, node, edge, scenario, property or source id is used once in the whole contract",
    "tag-known": "an area, node or edge carries a tag of its kind from the catalogue",
    "info-item": "an `info` key is an item of its element's tag, or an item every element of that kind may hold",
    "info-form": "an `info` value has the shape of its item's form: text, number, list, table, tree or code",
    "area-known": "a node's `area` is an area of its level, and every area holds one node at least",
    "edge-ends": "an edge joins two different nodes of its own level, one pair is joined once by one label in a direction, and the edge's id holds neither end's id",
    "edge-sentence": "a static edge's label opens in lower case, holds no full stop, question or exclamation mark, closes with no article, is more than a lone preposition and holds neither end's label; that it opens with a verb and that `<from label> <label> <to label>` is true is the writer's to check by the `read` call",
    "level-links": "`opens` names a level, every level but the first is opened by at least one node, and no chain of `opens` leads from a level back to it, so the first level is opened by none",
    "purpose-missing": "every node that is no state says its purpose",
    "state-region": "a state sits in an area tagged region, and a region holds only states",
    "region-initial": "a region's `initial` names one of its states",
    "transition-ends": "a transition joins two states of one region, only a transition joins two states, and none leaves a state marked `terminal`",
    "fact-paths": "a fact names two different paths of edges that start at one node and end at one node, none of them marked `many`",
    "scenario-steps": "a step names a node or an edge by its id and adds a note of 60 characters at most that holds a word, names neither end of its own edge and is no copy of its record's purpose, and one scenario at least is a principle",
    "property-form": "one invariant or property at least is stated; a property's kind, strength and status are known words, a gap alone names its fault, and each `on` names a node, an edge, an area, a level or a scenario",
    "evidence-source": "an evidence entry is a source id, `id:line` or `id:line-line`, and a node's `files` entry a source id; under --root each source path that is no url exists and holds the lines cited",
    "question-answered": "one rebuild question at least is asked; each names in `answers` the records that answer it, one at least with evidence, or in `gap` the gap property that says why none does, never both",
    "name-english": "a title, a label and a term are English and hold no Korean letter, the contract's, a level's and a scenario's title and an edge's label included; only a description may be Korean: a purpose, a meaning, an item's text, a step's note, a statement, a question",
    "korean-text": "a description that holds Korean keeps three forms: after a record's name `{id}` a particle of two forms is written as both, `은(는)`, `이(가)`, `을(를)`, `과(와)` or `(으)로`, since a new label may end in another sound; a sentence that closes with a full stop closes in `니다`; and no space stands before a particle after a name, a quote in backticks or an English word",
    "term-words": "a term's `avoid` lists the other words for its concept, and no text, label or title says one of them outside backticks: one concept keeps one word; an English word counts in any case and with a plural `s` or `es`, a Korean word alone or with a particle after it, and a word inside a longer word does not count; no word is both a term and a word to avoid",
    "text-plain": "a text names another record as `{id}`, which must exist, no text but a name, a source's words, an item of the code form and a quote in backticks spells the label of a node or an area: it names the record, so a rename reaches it; a label is two words or more, or the subject's own one-word name, and holds no other label and no space at either end, and a node's or an area's closes with no full stop and names no record; and a text holds no markup and no drawing value: outside backticks no `<` opens a word, a slash, `!` or `?`, whatever the word, and there is no hex colour, colour function, length in `px`, `x=` or `y=` number, or style declaration such as `left: 4`; an item of the code form is quoted as it is; every backtick a text opens is closed",
    "formula": f"a formula in a text, inline as `$...$` or display as `$$...$$`, is written in the subset the page draws: {SUBSET}; the contract's title, an area's or a node's label and a term hold none, since the page draws them as words",
}
TOPICS = (
    ("components and their purpose", lambda contract: len(nodes(contract)) - tagged(contract, "nodes", "state")),
    ("relations between components", lambda contract: len(edges(contract)) - tagged(contract, "edges", "transition")),
    ("layers and hierarchy", lambda contract: len(contract["levels"]) - 1),
    ("partitioning and boundaries", lambda contract: sum(len(level.get("areas", [])) for level in contract["levels"])),
    ("naming and placement conventions", lambda contract: kinds(contract, "convention")),
    ("coupling and dependency", lambda contract: tagged(contract, "edges", "dependsOn") + kinds(contract, "fact")),
    ("system documents", lambda contract: len(contract.get("sources", []))),
    ("state", lambda contract: tagged(contract, "nodes", "state", "dataStore", "queue")),
    ("control", lambda contract: tagged(contract, "nodes", "trigger", "router", "policy") + tagged(contract, "edges", "transition", "triggers", "sequence", "governs")),
    ("observation", lambda contract: items(contract, "signals")),
    ("interfaces and payloads", lambda contract: tagged(contract, "nodes", "endpoint") + sum(1 for edge in edges(contract) if edge.get("tag") in ("call", "publish", "access") and edge.get("info"))),
    ("failure and degraded behaviour", lambda contract: items(contract, "failure") + items(contract, "errors")),
    ("scenarios and operational principles", lambda contract: len(contract.get("scenarios", []))),
    ("invariants and properties", lambda contract: kinds(contract, "invariant") + kinds(contract, "property")),
    ("assumptions and constraints", lambda contract: kinds(contract, "assumption") + kinds(contract, "constraint")),
    ("domain terms and coined words", lambda contract: len(contract.get("terms", []))),
    ("rationale", lambda contract: items(contract, "why")),
    ("deployment and environment", lambda contract: tagged(contract, "nodes", "host") + tagged(contract, "areas", "deployment")),
    ("security and trust", lambda contract: tagged(contract, "nodes", "credential", "policy") + tagged(contract, "areas", "trustZone")),
    ("actors and outside systems", lambda contract: tagged(contract, "nodes", "actor")),
    ("gaps and open questions", lambda contract: kinds(contract, "gap")),
    ("evidence", lambda contract: sum(1 for element in elements(contract) if element.get("evidence"))),
)


def nodes(contract):
    return [node for level in contract["levels"] for node in level.get("nodes", [])]


def edges(contract):
    return [edge for level in contract["levels"] for edge in level.get("edges", [])]


def tagged(contract, kind, *tags):
    """How many elements of KIND, `nodes`, `edges` or `areas`, carry one of TAGS."""
    return sum(1 for level in contract["levels"] for element in level.get(kind, []) if element.get("tag") in tags)


def elements(contract):
    return nodes(contract) + edges(contract) + [area for level in contract["levels"] for area in level.get("areas", [])]


def kinds(contract, kind):
    return sum(1 for item in contract.get("properties", []) if item.get("kind") == kind)


def items(contract, name):
    return sum(1 for element in elements(contract) if name in element.get("info", {}))


def shown(text, labels, sentence=True):
    """TEXT with each `{id}` replaced by the label of the record it names, its first letter a capital where it opens TEXT, when TEXT is a SENTENCE, or follows a full stop, unless its first word is the subject's own name, such as a file name;
    in a Korean TEXT the label loses its article and gains no capital, since Korean has neither."""
    def label(match):
        found = labels.get(match.group(1), match.group(0))
        if KOREAN.search(text):
            return ARTICLE.sub("", found)
        plain = not OWN.search(found.split()[0]) if found.split() else False
        return found[:1].upper() + found[1:] if plain and (match.start() == 0 and sentence or text[:match.start()].endswith(". ")) else found
    return REFERENCE.sub(label, text)


def worded(contract, quoted):
    """Each text of CONTRACT that says something of the subject, and so may name a node, as (where, text): every text but an id, a label of a node or an area,
    the contract's title, a term, a source's own words and an item of the code form, whose identities QUOTED holds."""
    def own(holder, here, *names):
        return [pair for name in names for pair in placed(holder.get(name), f"{here}/{name}")]

    found = own(contract, "", "purpose")
    for k, entry in enumerate(contract.get("terms", [])):
        found += own(entry, f"terms/{k + 1}", "meaning")
    for level in contract["levels"]:
        here = f"levels/{level['id']}"
        found += own(level, here, "title", "about")
        for kind in ("areas", "nodes", "edges"):
            for element in level.get(kind, []):
                place = f"{here}/{kind}/{element['id']}"
                found += own(element, place, "purpose", *(["label"] if kind == "edges" else []))
                found += placed(element.get("info", {}), place + "/info", quoted)
    for scenario in contract.get("scenarios", []):
        here = f"scenarios/{scenario['id']}"
        found += own(scenario, here, "title", "purpose")
        for k, step in enumerate(scenario["steps"]):
            found += own(step, f"{here}/steps/{k + 1}", "note")
    for item in contract.get("properties", []):
        found += own(item, f"properties/{item['id']}", "statement", "fault")
    for question in contract.get("questions", []):
        found += own(question, f"questions/{question['id']}", "asks")
    return found


def placed(value, where="", skipped=()):
    """Every string VALUE holds, at any depth, but those whose identity is in SKIPPED, each as (where, text): WHERE is the way to it,
    an entry of a list named by its id, or by its count when it has none."""
    if id(value) in skipped:
        return []
    if isinstance(value, str):
        return [(where.lstrip("/") or "text", value)]
    if isinstance(value, list):
        value = {entry["id"] if isinstance(entry, dict) and isinstance(entry.get("id"), str) else k + 1: entry for k, entry in enumerate(value)}
    return [pair for key, part in value.items() for pair in placed(part, f"{where}/{key}", skipped)] if isinstance(value, dict) else []


def spelling(word):
    """A pattern for WORD as a text may say it: its parts whatever the space between them, a Korean word alone or with a particle after it,
    any other with a plural ending, and never inside a longer word."""
    return whole(word, PARTICLE if re.search(r"[가-힣]$", word) else r"(?:e?s)?")


def whole(words, ending=""):
    """A pattern for WORDS, whatever the space between them, then ENDING, never inside a longer word."""
    return r"(?<![\w-])" + r"\s+".join(re.escape(word) for word in words.split()) + ending + r"(?![\w-])"


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


OPTIONAL = {"avoid": list, "area": str, "opens": str, "purpose": str, "about": str, "note": str, "authority": str, "strength": str, "status": str, "fault": str,
            "many": bool, "principle": bool, "coined": bool, "on": list, "paths": list, "sources": list, "terms": list, "scenarios": list,
            "properties": list, "areas": list, "edges": list, "questions": list, "answers": list, "gap": str, "files": list}


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
        if isinstance(holder.get("avoid"), list) and not all(isinstance(word, str) and word.strip() for word in holder["avoid"]):
            found.append((where, "form", "`avoid` must be a list of words"))
        if "info" in holder and not isinstance(holder["info"], dict):
            found.append((where, "form", "`info` must be an object"))
        if "evidence" in holder and not (isinstance(holder["evidence"], list) and all(isinstance(entry, str) for entry in holder["evidence"])):
            found.append((where, "form", "`evidence` must be a list of strings"))
        if "basis" in holder and holder["basis"] not in BASES:
            found.append((where, "form", f"`basis` is one of {', '.join(BASES)}"))
        return True

    proof = ("info", "evidence", "basis")
    if not need("contract", contract, {"title": str, "purpose": str, "levels": list, "nodes": list}, ("sources", "terms", "scenarios", "properties", "questions", "areas", "edges")):
        return found
    for i, source in each("sources", contract.get("sources", [])):
        need(f"sources[{i}]", source, {"id": str, "path": str, "says": str}, ("authority",))
    for i, term in each("terms", contract.get("terms", [])):
        need(f"terms[{i}]", term, {"term": str, "meaning": str}, ("coined", "avoid"))
    levels = [level.get("id") for i, level in each("levels", contract.get("levels"), True) if need(f"levels[{i}]", level, {"id": str, "title": str}, ("about",))]
    shown = set()
    for kind, fields, optional in (("areas", {"id": str, "label": str, "tag": str, "level": str}, proof),
                                   ("nodes", {"id": str, "label": str, "tag": str, "level": str}, ("area", "opens", "purpose", "files") + proof),
                                   ("edges", {"id": str, "from": str, "to": str, "label": str, "tag": str}, ("many",) + proof)):
        for k, element in each(kind, contract.get(kind, [])):
            if need(f"{kind}[{k}]", element, fields, optional) and kind != "edges" and isinstance(element.get("level"), str):
                if element["level"] not in levels:
                    found.append((f"{kind}[{k}]", "form", f"`level` names `{element['level']}`, which is no level"))
                shown.update([element["level"]] if kind == "nodes" else [])
    found += [(f"level {name}", "form", "no node names this level; a level shows one node at least") for name in levels if isinstance(name, str) and name not in shown]
    for i, scenario in each("scenarios", contract.get("scenarios", [])):
        where = f"scenarios[{i}]"
        if need(where, scenario, {"id": str, "title": str, "purpose": str, "steps": list}, ("principle",)):
            for k, step in each(f"{where}.steps", scenario["steps"], True) if "steps" in scenario else ():
                need(f"{where}.steps[{k}]", step, {"at": str}, ("note",))
    for i, item in each("properties", contract.get("properties", [])):
        need(f"properties[{i}]", item, {"id": str, "kind": str, "statement": str}, ("strength", "status", "fault", "on", "paths", "evidence", "basis"))
    for i, question in each("questions", contract.get("questions", [])):
        need(f"questions[{i}]", question, {"id": str, "asks": str}, ("answers", "gap"))
        if isinstance(question, dict) and isinstance(question.get("answers"), list) and not all(isinstance(name, str) for name in question["answers"]):
            found.append((f"questions[{i}]", "form", "`answers` must be a list of ids"))
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
    contract = nested(contract)
    levels = {level["id"]: level for level in contract["levels"]}
    seen = {}
    named = [(f"level {level['id']}", level["id"]) for level in contract["levels"]]
    named += [(f"{level['id']}/{element['id']}", element["id"]) for level in contract["levels"] for kind in ("areas", "nodes", "edges") for element in level.get(kind, [])]
    named += [(f"source {source['id']}", source["id"]) for source in contract.get("sources", [])]
    named += [(f"{kind} {item['id']}", item["id"]) for kind in ("scenarios", "properties", "questions") for item in contract.get(kind, [])]
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
                found += [(where, "evidence-source", f"`files` names `{name}`, which is no source") for name in element.get("files", []) if not isinstance(name, str) or name not in sources]
        for area in level.get("areas", []):  # the page frames an area around its nodes, so one with none has nothing to draw
            if not any(node.get("area") == area["id"] for node in level["nodes"]):
                found.append((f"{home}/{area['id']}", "area-known", "holds no node; an area groups one node at least"))
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
            if node["tag"] != "state" and not node.get("purpose", "").strip():
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
    scenarios = contract.get("scenarios", [])
    everywhere = (set(levels) | {name for group in places.values() for name in group} | {area["id"] for level in contract["levels"] for area in level.get("areas", [])}
                  | {scenario["id"] for scenario in scenarios})
    purposes = {element["id"]: str(element["purpose"]).strip().rstrip(".").casefold() if "purpose" in element else None for element in elements(contract)}
    if not any(scenario.get("principle") is True for scenario in scenarios):
        found.append(("scenarios", "scenario-steps", "mark one scenario at least `principle: true`: the story that shows the purpose met"))
    for scenario in scenarios:
        for k, step in enumerate(scenario["steps"]):
            where = f"scenario {scenario['id']} step {k + 1}"
            if not any(step["at"] in group for group in places.values()):
                found.append((where, "scenario-steps", f"`{step['at']}` is no node or edge"))
            elif len(step.get("note", "")) > 60:
                found.append((where, "scenario-steps", "a step's own note is 60 characters at most; the record it names says the rest"))
            elif "note" in step and (not step["note"].strip() or step["note"].strip().rstrip(".").casefold() == purposes.get(step["at"])):
                found.append((where, "scenario-steps", "the note is empty or a copy of its record's purpose; a note adds what this step alone shows, so write that or leave the note out"))
            else:
                for end in sorted({end for edge in edges(contract) if edge["id"] == step["at"] for end in (edge["from"], edge["to"])}):
                    if "{" + end + "}" in step.get("note", ""):
                        found.append((where, "scenario-steps", f"the note names `{end}`, an end of its own edge; the edge says its ends, so a move of one would leave the note false"))
    if not any(item.get("kind") in ("invariant", "property") for item in contract.get("properties", [])):
        found.append(("properties", "property-form", "state one invariant or property at least: what must hold while the purpose is met"))
    labels = {element["id"]: element["label"] for element in elements(contract)}
    quoted = {id(value) for level in contract["levels"] for kind in ("area", "node", "edge") for element in level.get(kind + "s", [])
              for name, value in element.get("info", {}).items() if tag_items(kind, element["tag"]).get(name, {}).get("form") == "code"}
    for where, text in placed(contract, skipped=quoted):
        for tex, display in formulas(text):
            try:
                mathml(tex, display)
            except ValueError as error:
                found.append((where, "formula", f"`{tex}` in `{text[:40]}`: {error}; write it with {SUBSET} only, or quote it between backticks"))
        text = unformulated(text)
        if re.sub(r"```", "", text).count("`") % 2 or text.count("```") % 2:
            found.append((where, "text-plain", f"`{text[:40]}` opens a backtick it never closes; close the quote, since the page shows an open one as a mark"))
        for name in REFERENCE.findall(text):
            if name not in labels:
                found.append((where, "text-plain", f"`{{{name}}}` in `{text[:40]}` names no node, edge or area, the records a text can show by a label; quote the subject's own braces or markup in an item of the code form"))
        markup = MARKUP.search(re.sub(r"`[^`]*`", "", text)) or MARKUP.search(re.sub(r"`[^`]*`", "", shown(text, labels)))
        style = STYLE.search(re.sub(r"`[^`]*`", "", text))
        if style:
            found.append((where, "text-plain", f"`{style.group(0)}` in `{text[:40]}` reads as a colour, a size or a position; the page's code decides how a thing is drawn, so say what it is, or quote the subject's own value between backticks or in an item of the code form"))
        if markup:
            found.append((where, "text-plain", f"`{markup.group(0)}` in `{text[:40]}` reads as markup; the page's code decides how a text is drawn, so write a placeholder or the subject's own markup between backticks or in an item of the code form"))
    named = [element for element in elements(contract) if "from" not in element]
    for element in named:
        if len(element["label"].split()) < 2 and not OWN.search(element["label"]):
            found.append((element["id"], "text-plain", f"the label `{element['label']}` of `{element['id']}` is one common word, which no check can tell from prose; give it two words or more, or the subject's own name for it, such as a file name"))
    for level in contract["levels"]:
        for kind in ("areas", "nodes", "edges"):
            for element in level.get(kind, []):
                label = element["label"]
                if label != label.strip() or (kind != "edges" and (label.endswith(".") or REFERENCE.search(label))):
                    found.append((f"levels/{level['id']}/{kind}/{element['id']}/label", "text-plain", f"the label `{label}` holds a space at an end or, on a node or an area, a full stop at its end or `{{id}}`; a label is the bare words that name its record"))
    spelt = sorted(((whole(element["label"]), element["id"]) for element in named if element["label"].split()), key=lambda pair: -len(pair[0]))
    for pattern, name in spelt:
        for element in named:
            if element["id"] != name and re.search(pattern, element["label"], flags=re.IGNORECASE):
                found.append((element["id"], "text-plain", f"the label of `{element['id']}` spells the label of `{name}`, so a new name for `{name}` would leave it stale; give it words of its own"))
    said = worded(contract, quoted)
    for where, text in said:
        rest = re.sub(r"`[^`]*`|\{[a-z0-9-]+\}", "", text)
        for pattern, name in spelt:
            rest, count = re.subn(pattern, " ", rest, flags=re.IGNORECASE)
            if count:
                found.append((where, "text-plain", f"`{text[:40]}` spells the label of `{name}`; name it as `{{{name}}}`, so a new name reaches this text"))
    names = [("title", contract["title"])] + [(f"levels/{level['id']}/{kind}/{element['id']}/label", element["label"])
                                              for level in contract["levels"] for kind in ("areas", "nodes") for element in level.get(kind, [])]
    terms = {entry["term"].casefold(): entry["term"] for entry in contract.get("terms", [])}
    for where, name in names + [(f"terms/{k + 1}/term", entry["term"]) for k, entry in enumerate(contract.get("terms", []))]:
        if formulas(name):
            found.append((where, "formula", f"`{name[:40]}` holds a formula; the title, an area's or a node's label and a term draw no formula, so write it in words"))
    for where, name in names + [(f"terms/{k + 1}/term", entry["term"]) for k, entry in enumerate(contract.get("terms", []))] + [pair for pair in said if pair[0].endswith(("/title", "/label"))]:
        if KOREAN.search(name):
            found.append((where, "name-english", f"`{name[:40]}` holds Korean; a title, a label and a term stay English, and only a description may be Korean"))
    avoided = sorted(((word, entry["term"]) for entry in contract.get("terms", []) for word in entry.get("avoid", [])), key=lambda pair: -len(pair[0]))
    for word, term in avoided:
        if word.casefold() in terms:
            found.append((f"term {term}", "term-words", f"`{word}` is the term `{terms[word.casefold()]}` and a word to avoid for `{term}`; one word names one concept"))
    for where, text in said:
        if KOREAN.search(text) and not where.endswith(("/title", "/label")):
            bare = re.sub(r"`[^`]*`", "`", text)
            paired, apart = PAIRED.search(bare), APART.search(bare)
            if paired:
                found.append((where, "korean-text", f"`{text[:40]}` writes `{paired.group(1)}` after a name; a new label may end in another sound, so write both forms, such as `은(는)`, `을(를)` or `(으)로`, or a particle of one form"))
            if any(not ending.endswith("니다") for ending in ENDING.findall(bare)):
                found.append((where, "korean-text", f"`{text[:40]}` closes a sentence outside `니다`; a Korean description is in the formal polite form"))
            if apart:
                found.append((where, "korean-text", f"`{text[:40]}` puts a space before a particle in `{apart.group(0)}`; a particle joins the word before it"))
    for where, text in said + names:
        rest = re.sub(r"`[^`]*`|\{[a-z0-9-]+\}", " ", text)
        for word, term in avoided:
            rest, count = re.subn(spelling(word), " ", rest, flags=re.IGNORECASE)
            if count and word.casefold() not in terms:
                found.append((where, "term-words", f"`{text[:40]}` says `{word}` for the term `{term}`; one concept keeps one word, so write `{term}`, or quote the subject's own word between backticks"))
    all_edges = {edge['id']: edge for edge in edges(contract)}
    for item in contract.get("properties", []):
        where = f"property {item['id']}"
        found += [(where, "evidence-source", message) for entry in item.get("evidence", []) for message in cited(entry, sources, root)]
        if item["kind"] not in KINDS or item.get("strength", "must") not in STRENGTHS or item.get("status", "holds") not in STATUSES:
            found.append((where, "property-form", f"kind is one of {', '.join(KINDS)}; strength of {', '.join(STRENGTHS)}; status of {', '.join(STATUSES)}"))
        if item["kind"] == "gap" and item.get("fault") not in FAULTS or item["kind"] != "gap" and "fault" in item:
            found.append((where, "property-form", f"a gap, and only a gap, names its fault: one of {', '.join(FAULTS)}"))
        for name in item.get("on", []):
            if name not in everywhere:
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
            elif any(all_edges[key].get("many") for path in paths for key in path):
                found.append((where, "fact-paths", "a path crosses an edge marked `many`, which leads to several things, so the two paths cannot be said to agree"))
    stated = {item["id"]: item for item in contract.get("properties", [])}
    proven = {element["id"] for element in elements(contract) if element.get("evidence")} | {name for name, item in stated.items() if item.get("evidence")}
    if not contract.get("questions"):
        found.append(("questions", "question-answered", "ask one rebuild question at least: what a reader must learn from the contract to rebuild the subject"))
    for question in contract.get("questions", []):
        where, answers, gap = f"question {question['id']}", question.get("answers") or [], question.get("gap")
        for name in answers:
            if name not in everywhere and name not in stated:
                found.append((where, "question-answered", f"`answers` names `{name}`, which is no node, edge, area, level, scenario or property"))
        if bool(answers) == bool(gap):
            found.append((where, "question-answered", "holds both `answers` and `gap`; keep the one that is true" if answers else "has no answer: name the records that answer it in `answers`, or the gap property that says why none does in `gap`"))
        elif answers and not proven & set(answers):
            found.append((where, "question-answered", "no record in `answers` carries `evidence`, so the answer has no source"))
        elif gap and stated.get(gap, {}).get("kind") != "gap":
            found.append((where, "question-answered", f"`gap` names `{gap}`, which is no gap property"))
    return found


def step_lines(scenario, said, labels):
    """Each step of SCENARIO as a numbered line: what SAID holds for its edge, or its node's label, then its note."""
    return [f"  {k + 1}. {said.get(step['at'], labels.get(step['at']))}" + (f" ({shown(step['note'], labels)})" if "note" in step else "")
            for k, step in enumerate(scenario["steps"])]


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
        lines.append(f"\nlevel {level['id']}: {shown(level['title'], labels)}")
        for opener in openers.get(level["id"], []):
            lines.append(f"  opened by: {opener}")
        for node in level["nodes"]:
            if "opens" in node:
                lines.append(f"  opens: {node['label']} -> {node['opens']}")
        for area in level.get("areas", []):
            inside = [node["label"] for node in level["nodes"] if node.get("area") == area["id"]]
            if area["tag"] == "region":
                lines.append(f"  region: {area['label']} is in one of: {', '.join(inside)}; first {labels.get(area.get('info', {}).get('initial'), '?')}")
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
                said[edge["id"]] = f"{labels[edge['from']]} -- {shown(edge['label'], labels)}{guard}{action} --> {labels[edge['to']]}"
                lines.append(f"  transition: {said[edge['id']]}")
            else:
                said[edge["id"]] = f"{labels[edge['from']]} {shown(edge['label'], labels)} {'each of ' if edge.get('many') else ''}{labels[edge['to']]}."
                lines.append(f"  sentence: {said[edge['id']]}")
    for scenario in contract.get("scenarios", []):
        lines.append(f"\n{'principle' if scenario.get('principle') else 'scenario'} {scenario['id']}: {shown(scenario['title'], labels)} ({shown(scenario['purpose'], labels)})")
        lines += step_lines(scenario, said, labels)
    for item in contract.get("properties", []):
        lines.append(f"\n{item['kind']} {item['id']} ({item.get('strength', 'must')}, {item.get('status', 'holds')}): {shown(item['statement'], labels)}")
    return lines


def flat(value, labels):
    """An item's VALUE on one line, as phrases: a list's entries, a table's rows and a tree's branches joined by `; `."""
    if isinstance(value, dict):
        return "; ".join(" | ".join(shown(str(cell), labels, False) for cell in row) for row in value.get("rows", []))
    if isinstance(value, list):
        return "; ".join(flat(entry, labels) if not isinstance(entry, dict) else shown(entry.get("name", ""), labels, False) + (f" ({shown(entry['note'], labels, False)})" if entry.get("note") else "")
                         + (f" [{flat(entry['children'], labels)}]" if entry.get("children") else "") for entry in value)
    return shown(str(value), labels, False)


def outline_lines(contract, only=None):
    """The contract as leads to read from the top, or the level ONLY alone: the contract's purpose, each level's `about` over its areas, each area's `purpose`, or else its `why`,
    over its nodes, each node's purpose over its items, then each scenario's purpose over its steps, each term and each statement."""
    labels = {element["id"]: element["label"] for element in elements(contract)}
    said = {edge["id"]: f"{labels[edge['from']]} {shown(edge['label'], labels)} {labels[edge['to']]}" for edge in edges(contract)}
    lines = [] if only else [f"{contract['title']}: {shown(contract['purpose'], labels)}"]
    for level in contract["levels"]:
        if only not in (None, level["id"]):
            continue
        lines.append(f"\nlevel {level['id']}: {shown(level['title'], labels)}: {shown(level.get('about', '(no about)'), labels)}")
        def part(kind, element, lead, indent):
            catalogue_labels = {name: item["label"] for name, item in tag_items(kind, element["tag"]).items()}
            said = element.get(lead) if kind == "node" else element.get("info", {}).get(lead)
            return ([f"{indent}{element['label']} ({element['tag']})" + (f": {shown(said, labels)}" if isinstance(said, str) else "")]
                    + [f"{indent}  {catalogue_labels.get(name, name)}: {flat(value, labels)}" for name, value in element.get("info", {}).items() if kind == "node" or name != lead]
                    + ([f"{indent}  opens: level {element['opens']}"] if "opens" in element else []))
        for area in level.get("areas", []):
            lines += part("area", area, "purpose" if "purpose" in area.get("info", {}) else "why", "  ")
            lines += [line for node in level["nodes"] if node.get("area") == area["id"] for line in part("node", node, "purpose", "    ")]
        lines += [line for node in level["nodes"] if node.get("area") not in [area["id"] for area in level.get("areas", [])] for line in part("node", node, "purpose", "  ")]
    if only:
        return lines
    for scenario in contract.get("scenarios", []):
        lines.append(f"\n{'principle' if scenario.get('principle') else 'scenario'} {scenario['id']}: {shown(scenario['title'], labels)}: {shown(scenario['purpose'], labels)}")
        lines += step_lines(scenario, said, labels)
    lines += [""] + [f"term {entry['term']}: {shown(entry['meaning'], labels)}" for entry in contract.get("terms", [])]
    lines += [""] + [f"{item['kind']} {item['id']}: {shown(item['statement'], labels)}" for item in contract.get("properties", [])]
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
    """The tag catalogue the file at PATH holds, or None when it is no catalogue the calls can read."""
    try:
        tags = json.loads(pathlib.Path(path).read_text())
        whole = tags["forms"] == CATALOGUE["forms"]
        for kind in ("node", "edge", "area"):
            entries = list(tags[kind].values()) + [{"meaning": "", "items": tags["common"][kind]}]
            items = [item for entry in entries for item in entry["items"]]
            whole = (whole and all(isinstance(entry["meaning"], str) and isinstance(entry["items"], list) for entry in entries)
                     and all(isinstance(item["name"], str) and isinstance(item["label"], str) and bool(item["label"]) and item["label"] == item["label"].strip() and not MARKUP.search(item["label"]) and not KOREAN.search(item["label"]) and item["form"] in tags["forms"] and isinstance(item["example"], str) and bool(item["example"].strip())
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
    if args == ["rules"]:
        for rule, asks in RULES.items():
            print(f"{rule}: {asks}")
        return 0
    if args == ["fixtures"]:
        failed = 0
        held = dict(copies(HERE.parent / "fixtures"))
        for name, contract in held.items():
            rules = {rule for _, rule, _ in breaks(contract, HERE.parent)}
            wanted = {rule for rule in RULES if name == rule or name.startswith(rule + "-")}
            if rules != wanted:
                failed += 1
                print(f"FAIL {name}: broke {', '.join(sorted(rules)) or 'nothing'}, expected {', '.join(wanted) or 'nothing'}")
        missing = sorted(set(RULES) - set(held))
        for rule in missing:
            print(f"FAIL no fixture breaks {rule}")
        print("FAIL" if failed or missing else "PASS")
        return 1 if failed or missing else 0
    root, unread = None, ""
    while len(args) >= 4 and args[-2] in ("--root", "--tags"):
        option, value, args = args[-2], args[-1], args[:-2]
        if option == "--root" and root is None and args[0] == "check":
            root = pathlib.Path(value)
        elif option == "--tags" and TAGS is CATALOGUE and args[0] in ("check", "read"):
            TAGS = catalogue(value) or CATALOGUE
            if TAGS is CATALOGUE:
                unread, args = f"{value} holds no tag catalogue\n", []
        else:
            args = []
    only = args.pop() if len(args) == 3 and args[0] == "outline" and not args[2].startswith("-") else None
    if len(args) != 2 or args[0] not in ("check", "read", "outline", "gaps") or args[1].startswith("-"):
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
    contract = nested(contract)
    if args[0] == "read":
        print("\n".join(read_lines(contract)))
        return 0
    if args[0] == "outline":
        if only not in [None] + [level["id"] for level in contract["levels"]]:
            print(f"{only} is no level; one of {', '.join(level['id'] for level in contract['levels'])}", file=sys.stderr)
            return 1
        print("\n".join(outline_lines(contract, only)))
        return 0
    counts, asked = gap_lines(contract)
    print("what each topic holds:")
    print("\n".join(counts))
    print("\n".join([f"\n{len(asked)} open questions; answer each from the sources, or record a gap property `on` the element it names:"] + asked) if asked else "\nno open question")
    return 1 if asked else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Check a flow contract against its rules, and print a plan's time order.

usage: check-contract.py check CONTRACT.json [--root DIR]   print each break as `where: rule: message`, then `ok`, or the break count
                                                            on stderr; with --root, each source path must exist under DIR
usage: check-contract.py check CONTRACT.json --part PART    the same for the part PART alone, `top` or `levels/<id>`, reading of the
                                                            other parts only what its rules compare; --part may come once per part
usage: check-contract.py split CONTRACT.json FOLDER         write the contract's parts as files under FOLDER, `top.json` and
                                                            `levels/<id>.json`, and print each path
usage: check-contract.py order CONTRACT.json                print each plan level's critical path as `critical-path <level> <n> tasks: <id> ...`,
                                                            the ids in order, milestones among them, then each of its records' place on the time axis
usage: check-contract.py tags                               print each tag with its meaning and the items it calls for
usage: check-contract.py rules                              print each rule and what it asks
usage: check-contract.py fixtures                           check every contract of fixtures/, a whole one or a copy `contract-copies.json`
                                                            holds as changes to one, with the skill's folder as its root: one whose name opens
                                                            with a rule's must break that rule alone, any other must pass; prints `ok <name>`
                                                            or `refused <name>: <rules>` per contract, `FAIL <reason>` per miss, then PASS or FAIL

CONTRACT.json may be a folder of part files that `split` wrote.

Exit status 0 means ok, 1 a break, 2 a call it cannot read."""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from contract_copies import copies  # noqa: E402
from contract_core import FIELDS as CORE_FIELDS, RULES as CORE, SLUG, area_breaks, claim_breaks, id_breaks, question_breaks, record_breaks, source_breaks  # noqa: E402
from contract_fields import cited, fits, tag_items  # noqa: E402
from contract_parts import FLOW, checked, load, split_to  # noqa: E402
from contract_prose import MARKUP, REFERENCE, text_breaks, wording_breaks  # noqa: E402
from contract_tags import catalogue  # noqa: E402
from flow_order import before, critical, cycle, ranks  # noqa: E402
from tex_mathml import SUBSET  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
TAGS = catalogue(HERE.parent / "assets" / "tags.json")
LEVEL_KINDS = ("interaction", "plan")
PLAN_EDGES = ("request", "wait")
FRAGMENTS = {"alt": 2, "opt": 1, "loop": 1, "par": 2, "break": 1}  # each kind's least operand count; only alt and par hold more
ARTICLE = re.compile(r"^(?:an?|the)\s+", re.IGNORECASE)
OWN = re.compile(r"[./_\d]|[a-z][A-Z]")
RULES = {
    "form": "every part holds its required fields, each of the right type, and no other field",
    "unique-ids": CORE["unique-ids"],
    "tag-known": "a node, an edge or a task carries a tag of its kind from the catalogue; a plan's edge is a `request` or a `wait`, an interaction's never one",
    "info-item": "an `info` key is an item of its record's tag, or an item every record of that kind may hold",
    "info-form": "an `info` value has the shape of its item's form: text, number, list, table, tree or code",
    "area-known": CORE["area-known"],
    "level-nodes": "a level lists in `nodes` the nodes it draws, each once, in order across the top or down the left, and every node is listed by one level at least",
    "level-links": "an edge's `opens` names a level, every level but the first is opened by one edge at least, and no chain of `opens` leads from a level back to it",
    "edge-ends": "an interaction's edge joins two nodes its level lists, and a plan's edge two different tasks of its level; a pair is joined once by one label in a direction",
    "call-failure": "a `call` between nodes of two areas names its failure in a `failure` or `errors` item",
    "work-area": "an edge's `work` table has the columns `area`, `change` and `says`, and each row names an area by its id",
    "task-place": "a task sits in a plan level, on a node that level lists",
    "fragment-span": "a fragment sits in an interaction level with its kind's operands, two or more for `alt` and `par`, one for `opt`, `loop` and `break`, each naming edges of its level that follow one another, every operand but a `par`'s saying its guard; the operands follow one another, and two fragments nest or stand apart",
    "after-known": "an `after` names a milestone, edge or task of its own level, never itself",
    "milestone-order": "no precedence crosses a milestone backwards: nothing the milestone waits on comes after something that waits on the milestone",
    "order-acyclic": "the precedence of a level, an interaction's edge order, its `after` and a plan's edges, holds no cycle",
    "purpose-missing": "every node and every task says its purpose",
    "claim-form": CORE["claim-form"],
    "claim-paths": CORE["claim-paths"],
    "evidence-source": CORE["evidence-source"],
    "question-answered": CORE["question-answered"],
    "name-form": "a node's, an area's, a task's and a milestone's label opens with a capital, or with the subject's own name, and with no article; a level's and a claim's title is a slug",
    "name-english": "a title, a label and a term are English and hold no Korean letter; only a description may be Korean",
    "korean-text": "a description that holds Korean writes a two-form particle after `{id}` as both forms, closes a sentence in `니다`, and puts no space before a particle",
    "term-words": "no text says a word a term's `avoid` lists, and no word is both a term and a word to avoid",
    "text-plain": "a text names a node, an edge, a task or a milestone as `{id}`, which must exist, and spells no label of another; an edge's label is drawn as written, so it holds no backtick; no text holds markup or a drawing value outside backticks",
    "formula": f"a formula, inline as `$...$` or display as `$$...$$`, is written in the subset the page draws: {SUBSET}; a label and a term hold none",
}
FIELDS = {
    "contract": ({"title": str, "purpose": str, "areas": list, "levels": list, "nodes": list}, {"sources": list, "terms": list, "edges": list, "tasks": list, "fragments": list, "milestones": list, "claims": list, "questions": list}),
    **{kind: CORE_FIELDS[kind] for kind in ("sources", "terms", "areas")},
    "levels": ({"id": str, "title": str, "kind": str, "nodes": list}, {"about": str}),
    "nodes": ({"id": str, "label": str, "tag": str, "area": str}, {"purpose": str, "info": dict, "evidence": list, "basis": str}),
    "edges": ({"id": str, "level": str, "from": str, "to": str, "label": str, "tag": str}, {"opens": str, "after": list, "info": dict, "evidence": list, "basis": str}),
    "tasks": ({"id": str, "level": str, "node": str, "label": str, "tag": str}, {"purpose": str, "after": list, "info": dict, "evidence": list, "basis": str}),
    "fragments": ({"id": str, "level": str, "kind": str, "operands": list}, {"evidence": list, "basis": str}),
    "operands": ({"edges": list}, {"guard": str}),
    "milestones": ({"id": str, "level": str, "label": str, "after": list}, {"purpose": str, "evidence": list, "basis": str}),
    **{kind: CORE_FIELDS[kind] for kind in ("claims", "questions")},
}
LISTED = ("sources", "terms", "areas", "levels", "nodes", "edges", "tasks", "fragments", "milestones", "claims", "questions")
TEXT_LISTS = ("after", "nodes", "edges", "evidence")


def form_breaks(contract):
    """Breaks of the `form` rule; any of them stops the other rules, which read the fields freely."""
    found = []

    def need(where, holder, kind):
        found.extend(record_breaks(where, holder, *FIELDS[kind]))
        for name in TEXT_LISTS:
            if isinstance(holder, dict) and name in holder and kind not in ("contract", *CORE_FIELDS) and not (isinstance(holder[name], list) and all(isinstance(entry, str) and entry.strip() for entry in holder[name])):
                found.append((where, "form", f"`{name}` must be a list of strings"))

    need("contract", contract, "contract")
    if found:
        return found
    for kind in LISTED:
        for k, record in enumerate(contract.get(kind, [])):
            need(f"{kind}[{k}]", record, kind)
            if kind == "fragments" and isinstance(record, dict) and isinstance(record.get("operands"), list):
                for j, operand in enumerate(record["operands"]):
                    need(f"{kind}[{k}].operands[{j}]", operand, "operands")
    for kind in ("areas", "levels", "nodes"):
        if not contract[kind]:
            found.append((kind, "form", "is empty; it holds one entry at least"))
    for k, milestone in enumerate(contract.get("milestones", [])):
        if isinstance(milestone, dict) and milestone.get("after") == []:
            found.append((f"milestones[{k}]", "form", "`after` is empty; a milestone follows one record at least"))
    return found


def placed(value, where, skipped=()):
    """Every string VALUE holds, at any depth, but those whose identity is in SKIPPED, each as (where, text)."""
    if id(value) in skipped:
        return []
    if isinstance(value, str):
        return [(where, value)]
    if isinstance(value, list):
        return [pair for k, part in enumerate(value) for pair in placed(part, f"{where}/{k + 1}", skipped)]
    return [pair for key, part in value.items() for pair in placed(part, f"{where}/{key}", skipped)] if isinstance(value, dict) else []


def order_breaks(contract, level):
    """Breaks of `after-known`, `milestone-order` and `order-acyclic` on LEVEL."""
    found = []
    first = before(contract, level)
    milestones = {milestone["id"] for milestone in contract.get("milestones", []) if milestone["level"] == level["id"]}
    for kind in ("edges", "tasks", "milestones"):
        for record in contract.get(kind, []):
            if record["level"] == level["id"]:
                for name in record.get("after", []):
                    if name not in first or name == record["id"]:
                        found.append((f"{kind} {record['id']}", "after-known", f"`after` names `{name}`, which is no other milestone, edge or task of level `{level['id']}`"))
    loop = cycle(first)
    if loop:
        crossed = [name for name in loop if name in milestones]
        if crossed:
            found.append((f"level {level['id']}", "milestone-order", f"{' then '.join(loop + loop[:1])} crosses the milestone `{crossed[0]}` backwards: "
                          "what the milestone waits on comes after what waits on it; move the record to its side of the milestone"))
        else:
            found.append((f"level {level['id']}", "order-acyclic", f"{' then '.join(loop + loop[:1])} come each before the next; break the cycle"))
    return found


def fragment_breaks(contract, level):
    """Breaks of `fragment-span` on LEVEL."""
    found = []
    order = [edge["id"] for edge in contract.get("edges", []) if edge["level"] == level["id"]]
    spans = []
    for fragment in contract.get("fragments", []):
        if fragment["level"] != level["id"]:
            continue
        where = f"fragment {fragment['id']}"
        operands = fragment["operands"]
        if level["kind"] != "interaction":
            found.append((where, "fragment-span", "sits in a plan level; a fragment frames the edges of an interaction"))
            continue
        if fragment["kind"] not in FRAGMENTS or not (len(operands) == 1 if FRAGMENTS[fragment["kind"]] == 1 else len(operands) >= FRAGMENTS[fragment["kind"]]):
            found.append((where, "fragment-span", f"kind is one of {', '.join(FRAGMENTS)}, `alt` and `par` with two operands or more, any other with one"))
            continue
        named = [name for operand in operands for name in operand["edges"]]
        if not all(operand["edges"] for operand in operands) or any(name not in order for name in named):
            found.append((where, "fragment-span", "an operand names no edge, or one that is no edge of its level"))
            continue
        at = [order.index(name) for name in named]
        if at != list(range(at[0], at[0] + len(at))):
            found.append((where, "fragment-span", "the operands' edges do not follow one another in the level's order; list them in that order, with no other edge between"))
            continue
        if fragment["kind"] != "par" and not all(operand.get("guard", "").strip() for operand in operands):
            found.append((where, "fragment-span", "an operand says no guard; say when it runs, such as `the name is free`"))
        spans.append((at[0], at[-1], fragment["id"]))
    for start, end, name in spans:
        for other_start, other_end, other in spans:
            if name < other and start <= other_end and other_start <= end and not (start <= other_start and other_end <= end or other_start <= start and end <= other_end):
                found.append((f"fragment {name}", "fragment-span", f"overlaps `{other}` without holding it or sitting inside it; fragments nest or stand apart"))
    return found


def breaks(contract, root=None):
    """Every break of CONTRACT as (where, rule, message), in the order a reader meets them."""
    found = form_breaks(contract)
    if found:
        return found
    records = {kind: contract.get(kind, []) for kind in LISTED}
    named = [(f"{kind} {record['id']}", record["id"]) for kind in LISTED for record in records[kind] if "id" in record]
    found += id_breaks(named)
    seen = {name for _, name in named}
    levels = {level["id"]: level for level in records["levels"]}
    nodes = {node["id"]: node for node in records["nodes"]}
    tasks = {task["id"]: task for task in records["tasks"]}
    areas = {area["id"] for area in records["areas"]}
    sources = {source["id"]: source for source in records["sources"]}
    found += source_breaks(sources, root)
    for kind, catalogue in (("nodes", "node"), ("edges", "edge"), ("tasks", "task")):
        for record in records[kind]:
            where = f"{kind} {record['id']}"
            if record["tag"] not in TAGS[catalogue]:
                found.append((where, "tag-known", f"`{record['tag']}` is no {catalogue} tag; one of {', '.join(TAGS[catalogue])}"))
            elif kind == "edges" and record["level"] in levels and (record["tag"] in PLAN_EDGES) != (levels[record["level"]]["kind"] == "plan"):
                found.append((where, "tag-known", f"`{record['tag']}` does not fit a {levels[record['level']]['kind']} level; a plan's edge is one of {', '.join(PLAN_EDGES)}, an interaction's any other"))
            items = tag_items(TAGS, catalogue, record["tag"])
            for name, value in record.get("info", {}).items():
                if name not in items:
                    found.append((where, "info-item", f"`{name}` is no item of `{record['tag']}`; one of {', '.join(items)}"))
                elif not fits(value, items[name]["form"]):
                    found.append((where, "info-form", f"`{name}` is no {items[name]['form']}, the form its item takes"))
            found += [(where, "evidence-source", message) for entry in record.get("evidence", []) for message in cited(entry, sources, root)]
            if kind != "edges" and not record.get("purpose", "").strip():
                found.append((where, "purpose-missing", "say what it is for, in one sentence"))
    found += area_breaks(records["areas"], records["nodes"], lambda record: f"{'nodes' if 'tag' in record else 'areas'} {record['id']}")
    for area in records["areas"]:
        found += [(f"areas {area['id']}", "evidence-source", message) for entry in area.get("evidence", []) for message in cited(entry, sources, root)]
    listed = set()
    for level in records["levels"]:
        where = f"levels {level['id']}"
        if level["kind"] not in LEVEL_KINDS:
            found.append((where, "form", f"`kind` is one of {', '.join(LEVEL_KINDS)}"))
            return found
        if not level["nodes"] or len(set(level["nodes"])) != len(level["nodes"]) or any(name not in nodes for name in level["nodes"]):
            found.append((where, "level-nodes", "`nodes` is empty, lists a node twice, or names one that is no node"))
        listed.update(level["nodes"])
    found += [(f"nodes {name}", "level-nodes", "no level lists it; add it to the `nodes` of the level that draws it") for name in nodes if name not in listed]
    opened = {name: [] for name in levels}
    for edge in records["edges"]:
        where = f"edges {edge['id']}"
        if edge["level"] not in levels:
            found.append((where, "edge-ends", f"`level` names `{edge['level']}`, which is no level"))
            continue
        level = levels[edge["level"]]
        if "opens" in edge:
            if edge["opens"] in levels:
                opened[edge["opens"]].append(edge["level"])
            else:
                found.append((where, "level-links", f"`opens` names `{edge['opens']}`, which is no level"))
        if level["kind"] == "interaction" and not (edge["from"] in level["nodes"] and edge["to"] in level["nodes"]):
            found.append((where, "edge-ends", f"joins `{edge['from']}` and `{edge['to']}`; an interaction's edge joins two nodes level `{level['id']}` lists"))
        sides = {nodes.get(end, {}).get("area") for end in (edge["from"], edge["to"])}
        crosses = len(sides) == 2 and sides <= areas  # an unknown area breaks area-known alone
        if level["kind"] == "interaction" and edge["tag"] == "call" and crosses and not {"failure", "errors"} & set(edge.get("info", {})):
            found.append((where, "call-failure", "crosses from one area to another and names no failure; say what the caller sees when it fails in `failure` or `errors`"))
        owed = edge.get("info", {}).get("work")
        if isinstance(owed, dict) and isinstance(owed.get("rows"), list):  # a work value of another shape breaks info-form alone
            if owed.get("columns") != ["area", "change", "says"]:
                found.append((where, "work-area", "`work` has the columns `area`, `change` and `says`, in that order"))
            found += [(where, "work-area", f"a `work` row names `{row[0]}`, which is no area") for row in owed["rows"] if isinstance(row, list) and row and not isinstance(row[0], (list, dict)) and row[0] not in areas]  # a list or dict cell breaks info-form alone
        if level["kind"] == "plan" and not (tasks.get(edge["from"], {}).get("level") == level["id"] == tasks.get(edge["to"], {}).get("level") and edge["from"] != edge["to"]):
            found.append((where, "edge-ends", f"joins `{edge['from']}` and `{edge['to']}`; a plan's edge joins two different tasks of level `{level['id']}`"))
    pairs = {}
    for edge in records["edges"]:
        key = (edge["level"], edge["from"], edge["to"], edge["label"])
        if key in pairs:
            found.append((f"edges {edge['id']}", "edge-ends", f"joins the same ends by the same label as `{pairs[key]}`; one exchange is one edge"))
        pairs.setdefault(key, edge["id"])
    first = records["levels"][0]["id"]
    for name, by in opened.items():
        if name == first and by:
            found.append((f"levels {name}", "level-links", "the first level is the whole subject, so no edge opens it"))
        elif name != first and not by:
            found.append((f"levels {name}", "level-links", "no edge opens it; name it in the `opens` of the edge whose inside it shows"))
    reached, path = set(), [first]
    while path:
        name = path.pop()
        if name not in reached:
            reached.add(name)
            path += [edge["opens"] for edge in records["edges"] if edge["level"] == name and edge.get("opens") in levels]
    found += [(f"levels {name}", "level-links", "no chain of `opens` from the first level reaches it") for name in levels if name not in reached and opened[name]]
    for task in records["tasks"]:
        level = levels.get(task["level"])
        if not level or level["kind"] != "plan" or task["node"] not in level["nodes"]:
            found.append((f"tasks {task['id']}", "task-place", f"sits on `{task['node']}` in `{task['level']}`; a task sits in a plan level, on a node it lists"))
    for kind in ("fragments", "milestones"):
        for record in records[kind]:
            if record["level"] not in levels:
                found.append((f"{kind} {record['id']}", "form", f"`level` names `{record['level']}`, which is no level"))
    if any(rule == "form" for _, rule, _ in found):  # a record at no level would break the order rules of the level it was meant for
        return found
    for level in records["levels"]:
        found += fragment_breaks(contract, level) + order_breaks(contract, level)
    for kind in ("fragments", "milestones"):
        for record in records[kind]:
            found += [(f"{kind} {record['id']}", "evidence-source", message) for entry in record.get("evidence", []) for message in cited(entry, sources, root)]
    everywhere = seen - set(sources) - {question["id"] for question in records["questions"]}
    stated = {claim["id"]: claim for claim in records["claims"]}
    found += claim_breaks(records["claims"], sources, root, everywhere - set(stated), {edge["id"]: edge for edge in records["edges"]})
    proven = {record["id"] for kind in LISTED for record in records[kind] if isinstance(record, dict) and record.get("evidence")}
    found += question_breaks(records["questions"], everywhere, proven, stated)
    return found + prose_breaks(contract, records)


def prose_breaks(contract, records):
    """Breaks of the prose rules lib's checks hold, and of `name-form`."""
    found = []
    labelled = [(kind, record) for kind in ("nodes", "edges", "tasks", "milestones") for record in records[kind]]
    labels = {record["id"]: record["label"] for _, record in labelled}
    quoted = {id(value) for kind, catalogue in (("nodes", "node"), ("edges", "edge"), ("tasks", "task")) for record in records[kind]
              for name, value in record.get("info", {}).items() if tag_items(TAGS, catalogue, record["tag"]).get(name, {}).get("form") == "code"}
    edge_labels = {id(edge["label"]) for edge in records["edges"]}
    said = []
    said += placed(contract.get("purpose"), "purpose")
    for k, entry in enumerate(records["terms"]):
        said += placed(entry["meaning"], f"terms/{k + 1}/meaning")
    for kind in LISTED:
        for record in records[kind]:
            where = f"{kind}/{record.get('id', '')}"
            for name in ("purpose", "about", "statement", "fault", "asks", "says"):
                said += placed(record.get(name), f"{where}/{name}") if kind != "sources" or name != "says" else []
            said += placed(record.get("info", {}), f"{where}/info", quoted)
            if kind == "fragments":
                said += [(f"{where}/operands/{j + 1}/guard", operand["guard"]) for j, operand in enumerate(record["operands"]) if "guard" in operand]
    texts = [pair for pair in placed(contract, "", quoted | edge_labels) if not pair[0].startswith(("/sources/", "/terms/")) or pair[0].endswith("/meaning")]
    found += text_breaks(texts, labels)
    for edge in records["edges"]:
        if "`" in edge["label"] or MARKUP.search(edge["label"]):
            found.append((f"edges/{edge['id']}/label", "text-plain", f"the label `{edge['label']}` holds a backtick or markup; an edge's label is drawn as written, such as `GET /v1/names/{{name}}`"))
    named = [(kind, record) for kind, record in labelled if kind != "edges"] + [("areas", area) for area in records["areas"]]
    for kind, record in named:
        label = record["label"]
        if label != label.strip() or label.endswith(".") or REFERENCE.search(label):
            found.append((f"{kind}/{record['id']}/label", "text-plain", f"the label `{label}` holds a space at an end, a full stop at its end or `{{id}}`; a label is the bare words that name its record"))
        if ARTICLE.match(label) or not (label[:1].isupper() or OWN.search(label.split()[0] if label.split() else "")):
            found.append((f"{kind}/{record['id']}/label", "name-form", f"the label `{label}` opens in lower case or with an article; open it with a capital and no article, such as `Name store`"))
    for kind in ("levels", "claims"):
        for record in records[kind]:
            if not SLUG.fullmatch(record["title"]):
                found.append((f"{kind} {record['id']}", "name-form", f"the title `{record['title'][:40]}` is no slug, lowercase words and digits joined by `-`"))
    names = [("title", contract["title"])] + [(f"{kind}/{record['id']}/label", record["label"]) for kind, record in named + [("edges", edge) for edge in records["edges"]]]
    found += wording_breaks(said, names, [(record["id"], record["label"]) for kind, record in named if kind != "areas"],
                            [(f"terms/{k + 1}/term", f"term {entry['term']}", entry) for k, entry in enumerate(records["terms"])])
    return found


def order_lines(contract):
    """Each plan level's critical path, then its places on the time axis."""
    lines = []
    for level in contract["levels"]:
        first = before(contract, level)
        if level["kind"] == "plan":
            tasks = {task["id"] for task in contract.get("tasks", []) if task["level"] == level["id"]}
            chain = critical(first, tasks)
            lines.append(f"critical-path {level['id']} {sum(1 for name in chain if name in tasks)} tasks: {' '.join(chain)}")
    for level in (level for level in contract["levels"] if level["kind"] == "plan"):
        rank = ranks(before(contract, level))
        lines += [f"place {level['id']} {name} {at}" for name, at in rank.items()]
    return lines


def main(args):
    if args == ["tags"]:
        for kind in ("node", "edge", "task"):
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
            print(f"refused {name}: {', '.join(sorted(rules))}" if rules else f"ok {name}")
            if rules != wanted:
                failed += 1
                print(f"FAIL {name}: broke {', '.join(sorted(rules)) or 'nothing'}, expected {', '.join(sorted(wanted)) or 'nothing'}")
        missing = sorted(rule for rule in RULES if not any(name == rule or name.startswith(rule + "-") for name in held))
        for rule in missing:
            print(f"FAIL no fixture breaks {rule}")
        print("FAIL" if failed or missing else "PASS")
        return 1 if failed or missing else 0
    if len(args) == 3 and args[0] == "split" and not any(arg.startswith("-") for arg in args[1:]):
        try:
            print("\n".join(str(path) for path in split_to(args[1], args[2], FLOW)))
        except (OSError, ValueError, RecursionError) as e:
            print(f"{args[1]}: {e}", file=sys.stderr)
            return 1
        return 0
    root, chosen = None, []
    while len(args) >= 4 and args[0] == "check" and args[-2] in ("--root", "--part") and not args[-1].startswith("-"):
        option, value, args = args[-2], args[-1], args[:-2]
        if option == "--part":
            chosen.append(value)
        elif root is None:
            root = pathlib.Path(value)
        else:
            args = []
    if len(args) != 2 or args[0] not in ("check", "order") or args[1].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        contract = load(args[1], FLOW)
        found = checked(contract, chosen, FLOW, lambda shown: breaks(shown, root)) if chosen else breaks(contract, root)
    except (OSError, ValueError, RecursionError) as e:  # a contract nested past Python's depth is refused, not a traceback
        print(f"{args[1]}: {e}", file=sys.stderr)
        return 1
    for where, rule, message in found:
        print(f"{where}: {rule}: {message}")
    if found:
        print(f"{len(found)} breaks; `check-contract.py rules` says what each rule asks", file=sys.stderr)
        return 1
    print("ok" if args[0] == "check" else "\n".join(order_lines(contract)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Draw a Schema document (../../schema/assets/schema.json) as Markdown with Mermaid, for chat.

usage: emit-mermaid.py doc.json                        print the levels as a file tree, then one Mermaid block per level,
                                                       top level first, each followed by its metadata as formats.md says
       emit-mermaid.py --split DIR doc.json            also write each level's Mermaid block to DIR/<n>-<level>.mmd
       emit-mermaid.py --check doc.json [--output F]   check the output, or the file F, opens with a tree of every level,
                                                       then one block per level in tree order holding its nodes and edges
       emit-mermaid.py losses [--doc F]                check every grammar construct has a row in mermaid.md's loss table
                                                       (or F's), and each row marked kept changes the output when changed
       emit-mermaid.py formats [--doc F]               check formats.md (or F) has one display row per format and reserved key

Exit status 0 means ok, 1 a problem found, 2 a usage error.
"""
import copy
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
INTERFACE_FOLDER = HERE.parent
SCHEMA_FOLDER = INTERFACE_FOLDER.parent / "schema"
GRAMMAR = json.loads((SCHEMA_FOLDER / "assets" / "schema.json").read_text())
LEVEL = GRAMMAR["$defs"]["level"]
FORMATS = list(GRAMMAR["$defs"]["format"])
RESERVED = list(GRAMMAR["$defs"]["meta"]["properties"])
KINDS = LEVEL["properties"]["kind"]["enum"]
DIFF_SIGN = {"added": "+", "removed": "−", "changed": "~"}
DIFF_TINT = {"added": "#2a7", "removed": "#c33", "changed": "#c90"}


def format_number(value):
    return str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)


def pointer(location):
    return f"[{location}]({location})" if re.match(r"https?://", location) else f"`{location}`"


# one display per format and reserved key; formats.md documents each, `formats` holds the two equal
SHOW_FORMAT = {
    "text": lambda name, value: value,
    "number": lambda name, value: format_number(value),
    "url": lambda name, value: f"[{name}]({value})",
    "ms": lambda name, value: f"{format_number(value)} ms",
    "percent": lambda name, value: f"{format_number(value)}%",
    "date": lambda name, value: value,
    "bool": lambda name, value: "yes" if value else "no",
}
SHOW_RESERVED = {
    "note": lambda value: f"_{value}_",
    "diff": lambda value: f"{DIFF_SIGN.get(value, '?')} {value}",
    "evidence": lambda value: ", ".join(pointer(location) for location in value),
    "constraint": lambda value: ", ".join(f"`{constraint}`" for constraint in value),
}


def show_metadata(metadata):
    out = []
    for k, value in metadata.items():
        if k in SHOW_RESERVED:
            out.append(f"{k}: {SHOW_RESERVED[k](value)}")
            continue
        name, _, format_name = k.rpartition("-")
        out.append(f"{name}: {SHOW_FORMAT[format_name](name, value)}" if format_name in SHOW_FORMAT else f"{k}: {value}")
    return "; ".join(out)


def levels(document):
    """Every level root first, as (level, id, depth, opener node): a level's id is its opener's id, or root."""
    out = []

    def visit(level, level_id, depth, opener):
        out.append((level, level_id, depth, opener))
        for node in level.get("nodes", []):
            if isinstance(node.get("opens"), dict):
                visit(node["opens"], node.get("id", "?"), depth + 1, node)
    if isinstance(document.get("level"), dict):
        visit(document["level"], "root", 0, None)
    return out


def mermaid_id(identifier):
    return "n_" + str(identifier).replace("-", "_")


def ends(target):
    # a port may join several nodes: one line per node
    return target if isinstance(target, list) else [target]


def quote(text):
    return '"' + str(text).replace('"', "#quot;").replace("<", "#lt;").replace(">", "#gt;") + '"'


def plain(text):
    # stateDiagram labels take no entities: keep them to characters its parser reads as text
    return re.sub(r"[\"{}:;]", "'", str(text)).replace("\n", " ")


def quantity_text(quantity):
    return f"{format_number(quantity['value'])}{(' ' + quantity['unit']) if quantity.get('unit') else ''} ({quantity['kind']})" if isinstance(quantity, dict) else ""


def node_text(node):
    text = node.get("label", node.get("id", "?"))
    if isinstance(node.get("opens"), dict):
        text += " ▸"
    return text


def edge_text(edge):
    marks = edge.get("mark", [])
    text = ("✗ " if "failure" in marks else "") + ("? " if "unsure" in marks else "") + edge.get("label", "")
    return text + (f" · {quantity_text(edge['qty'])}" if edge.get("qty") else "")


CLASSES = [
    "classDef happy stroke:#2a7,stroke-width:3px",
    "classDef failure stroke:#c33,stroke-width:2px",
    "classDef optional stroke-dasharray:4 3",
    "classDef unsure stroke:#999,stroke-dasharray:2 2",
    "classDef diffadded fill:#dfd,stroke:#2a7",
    "classDef diffremoved fill:#fdd,stroke:#c33,stroke-dasharray:4 3",
    "classDef diffchanged fill:#ffe9b3,stroke:#c90",
]


def classes(node):
    out = list(node.get("mark", []))
    if isinstance(node.get("meta"), dict) and node["meta"].get("diff") in DIFF_SIGN:
        out.append("diff" + node["meta"]["diff"])
    return out


def flowchart(level):
    kind = level.get("kind")
    lines = ["flowchart " + ("TB" if kind == "topology" else "LR")]
    links = 0
    styles = []

    def shape(node):
        label_text = quote(node_text(node) + (f"<br/>{quantity_text(node['qty'])}" if node.get("qty") else ""))
        if node.get("gate"):
            return f"{{{{{quote(node_text(node) + ' (' + node['gate'] + ')')}}}}}"
        if kind == "workflow":
            return f"({label_text})"
        if node.get("abstract"):
            return f"[/{label_text}/]"
        if node.get("singleton"):
            return f"[[{label_text}]]"
        return f"[{label_text}]"

    nodes = level.get("nodes", [])
    partitions = [item for item in level.get("partitions", []) if isinstance(item, dict)]
    placed = set()
    for partition in partitions:
        inside = [node for node in nodes if node.get("partition") == partition.get("id")]
        lines.append(f"  subgraph p_{mermaid_id(partition.get('id'))[2:]}[{quote(partition.get('label', partition.get('id')))}]")
        lines += [f"    {mermaid_id(node.get('id'))}{shape(node)}" for node in inside]
        lines.append("  end")
        placed |= {id(node) for node in inside}
    lines += [f"  {mermaid_id(node.get('id'))}{shape(node)}" for node in nodes if id(node) not in placed]
    for i, trigger in enumerate(level.get("triggers", [])):
        every = f" every {trigger['every']}" if trigger.get("every") else ""
        lines.append(f"  t_{i}((\" \")) -->|{quote(trigger.get('label', '') + every)}| {mermaid_id(trigger.get('to'))}")
        links += 1
    for i, port in enumerate(level.get("in", [])):
        for to in ends(port.get("to")):
            lines.append(f"  in_{i}>{quote(port.get('edge'))}] --> {mermaid_id(to)}")
            links += 1
    for i, port in enumerate(level.get("out", [])):
        for origin in ends(port.get("from")):
            lines.append(f"  {mermaid_id(origin)} --> out_{i}>{quote(port.get('edge'))}]")
            links += 1
    for edge in level.get("edges", []):
        marks = edge.get("mark", [])
        arrow = "==>" if "happy" in marks else "-.->" if set(marks) & {"failure", "optional", "unsure"} else "-->"
        label = edge_text(edge)
        lines.append(f"  {mermaid_id(edge.get('from'))} {arrow}{('|' + quote(label) + '|') if label else ''} {mermaid_id(edge.get('to'))}")
        diff = edge.get("meta", {}).get("diff") if isinstance(edge.get("meta"), dict) else None
        if diff in DIFF_TINT:
            styles.append(f"  linkStyle {links} stroke:{DIFF_TINT[diff]},stroke-width:3px")
        elif "failure" in marks:
            styles.append(f"  linkStyle {links} stroke:#c33")
        links += 1
    return lines + styles


HISTORY = {"shallow": "H", "deep": "H*"}   # Harel's marks


def superstate(node):
    """The state level a state opens, drawn inside it as a Harel superstate, or None."""
    opened_level = node.get("opens")
    return opened_level if isinstance(opened_level, dict) and opened_level.get("kind") == "state" else None


def history_states(node, level):
    """{mode: id} of the history states inside superstate n of level `level`: its level's own `history`, and each other
    mode an edge into it `enters` by, so that edge can point at it."""
    inner = superstate(node)
    if not inner or not inner.get("nodes"):
        return {}
    own = inner.get("history")
    modes = [own] + [edge.get("enters") for edge in level.get("edges", []) if edge.get("to") == node.get("id") and edge.get("from") != node.get("id")]
    modes = list(dict.fromkeys(mode for mode in modes if mode in HISTORY))
    first = mermaid_id(inner["nodes"][0].get("id"))[2:]
    # the first mode keeps the plain id, so a level with one history mark draws it as before
    return {mode: f"h_{first}" + ("" if i == 0 else f"_{mode}") for i, mode in enumerate(modes)}


def state_inside(level, indent, marks=None):
    """A state level's states, regions, history and events, each superstate holding its own level."""
    nodes = level.get("nodes", [])
    regions = [region for region in level.get("regions", []) if isinstance(region, dict)]
    initial = level.get("initial", [])
    initial = [initial] if isinstance(initial, str) else list(initial)
    triggered = {trigger.get("to") for trigger in level.get("triggers", [])}
    # an edge is drawn inside its region's block when both ends sit in it, else at the top
    group = {node.get("id"): (node.get("region") if regions else None) for node in nodes}
    marks = {level["history"]: f"h_{mermaid_id(nodes[0].get('id'))[2:]}"} if marks is None and level.get("history") in HISTORY and nodes else marks or {}
    into = {node.get("id"): history_states(node, level) for node in nodes}

    def state(node, state_indent):
        inner = superstate(node)
        if not inner:
            return [f"{state_indent}state \"{plain(node_text(node) + (' · ' + quantity_text(node['qty']) if node.get('qty') else ''))}\" as {mermaid_id(node.get('id'))}"]
        return [f"{state_indent}state \"{plain(node.get('label', node.get('id', '?')))}\" as {mermaid_id(node.get('id'))} {{"] + state_inside(inner, state_indent + "  ", into[node.get("id")]) + [f"{state_indent}}}"]

    def arrow(edge, arrow_indent):
        # an edge entering by history points at that history state, else at the superstate itself
        superstate_node = next((node for node in nodes if node.get("id") == edge.get("to")), {})
        inner = superstate(superstate_node) or {}
        mode = edge.get("enters") or inner.get("history")
        to = into.get(edge.get("to"), {}).get(mode) if edge.get("from") != edge.get("to") else None
        return f"{arrow_indent}{mermaid_id(edge.get('from'))} --> {to or mermaid_id(edge.get('to'))}" + (f" : {plain(edge_text(edge))}" if edge_text(edge) else "")

    def body(members, body_indent, top):
        ids = {node.get("id") for node in members}
        out = [line for node in members for line in state(node, body_indent)]
        for mode, history_id in (marks.items() if top else ()):   # entering the superstate again resumes where it was left
            out.append(f"{body_indent}state \"{HISTORY[mode]}\" as {history_id}")
        out += [f"{body_indent}[*] --> {mermaid_id(state_id)}" for state_id in initial if state_id in ids and state_id not in triggered]
        out += [f"{body_indent}[*] --> {mermaid_id(trigger.get('to'))} : {plain(trigger.get('label', ''))}"
                for trigger in level.get("triggers", []) if trigger.get("to") in ids]
        out += [arrow(edge, body_indent) for edge in level.get("edges", []) if edge.get("from") in ids and edge.get("to") in ids]
        out += [f"{body_indent}{mermaid_id(node.get('id'))} --> [*]" for node in members if node.get("final")]
        return out

    lines = []
    if regions:
        lines.append(f"{indent}state \"{plain(level.get('subject') or level.get('title', 'regions'))}\" as regions_{mermaid_id(nodes[0].get('id') if nodes else 'x')[2:]} {{")
        for i, region in enumerate(regions):
            if i:
                lines.append(f"{indent}  --")
            lines.append(f"{indent}  state \"{plain(region.get('label', region.get('id')))}\" as r_{mermaid_id(region.get('id'))[2:]} {{")
            lines += body([node for node in nodes if node.get("region") == region.get("id")], indent + "    ", False)
            lines.append(f"{indent}  }}")
        lines.append(f"{indent}}}")
    lines += body([node for node in nodes if group.get(node.get("id")) is None], indent, True)
    for edge in level.get("edges", []):
        from_id, to_id = edge.get("from"), edge.get("to")
        if from_id not in group or to_id not in group or group[from_id] != group[to_id]:
            lines.append(arrow(edge, indent))
    return lines


def state_diagram(level):
    lines = ["stateDiagram-v2", "  direction LR"] + state_inside(level, "  ")
    for port in level.get("in", []):
        lines += [f"  [*] --> {mermaid_id(to)} : {plain(port.get('edge'))}" for to in ends(port.get("to"))]
    for port in level.get("out", []):
        lines += [f"  {mermaid_id(origin)} --> [*] : {plain(port.get('edge'))}" for origin in ends(port.get("from"))]
    return lines


def mermaid(level):
    lines = state_diagram(level) if level.get("kind") == "state" else flowchart(level)
    # Mermaid styles no composite state, so a superstate keeps its marks only in the table
    styled = [node for node in level.get("nodes", []) if not (level.get("kind") == "state" and superstate(node))]
    used = sorted({class_name for node in styled for class_name in classes(node)})
    lines += [f"  {definition}" for definition in CLASSES if definition.split()[1] in used]
    for class_name in used:
        members = [mermaid_id(node.get("id")) for node in styled if class_name in classes(node)]
        lines.append(f"  class {','.join(members)} {class_name}")
    return "\n".join(lines)


def tree(document):
    out = []

    def visit(level, level_id, opener, lead, last, top):
        link = f", {opener['link']}" if opener and opener.get("link") else ""
        out.append(("" if top else lead + ("└── " if last else "├── ")) + f"{level_id}: {level.get('title', '')} ({level.get('kind')}{link})")
        kids = [node for node in level.get("nodes", []) if isinstance(node.get("opens"), dict)]
        for i, child in enumerate(kids):
            visit(child["opens"], child.get("id", "?"), child, "" if top else lead + ("    " if last else "│   "), i == len(kids) - 1, False)
    if isinstance(document.get("level"), dict):
        visit(document["level"], "root", None, "", True, True)
    return out


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def metadata_table(level):
    rows = []
    if isinstance(level.get("meta"), dict):
        rows.append(("this level", level["meta"]))
    rows += [(f"`{node.get('id')}` {node.get('label', '')}", node["meta"]) for node in level.get("nodes", []) if isinstance(node.get("meta"), dict)]
    rows += [(f"`{edge.get('from')}` → `{edge.get('to')}` {edge.get('label', '')}", edge["meta"])
             for edge in level.get("edges", []) if isinstance(edge.get("meta"), dict)]
    if not rows:
        return []
    return ["", "| element | metadata |", "| --- | --- |"] + [f"| {cell(element)} | {cell(show_metadata(metadata))} |" for element, metadata in rows]


def syncs(level):
    return [""] + [f"- sync `{sync.get('name')}`: on `{sync.get('when')}`" + (f" while `{sync['where']}`" if sync.get("where") else "")
                   + f", then `{sync.get('then')}`" for sync in level.get("syncs", [])] if level.get("syncs") else []


def emit(document):
    """The Markdown for a document, and each level's (id, Mermaid source) in tree order."""
    out = [f"## {document.get('title', 'Schema')}"]
    if isinstance(document.get("meta"), dict):
        out += ["", show_metadata(document["meta"])]
    out += ["", "```text", *tree(document), "```"]
    blocks = []
    for level, level_id, depth, opener in levels(document):
        source = mermaid(level)
        blocks.append((level_id, source))
        of = f" of {level['subject']}" if level.get("kind") == "state" and level.get("subject") else ""
        out += ["", f"### `{level_id}` {level.get('title', '')} ({level.get('kind')}{of})"]
        if level.get("why"):
            out += ["", f"_{level['why']}_"]
        out += ["", "```mermaid", source, "```"] + syncs(level) + metadata_table(level)
    return "\n".join(out) + "\n", blocks


def check(document, text):
    problems = []
    fences = re.findall(r"^```(\w*)\n(.*?)^```$", text, re.S | re.M)
    level_list = levels(document)
    if not fences or fences[0][0] != "text":
        return ["the output does not open with a text block of the level tree"]
    tree_ids = [re.sub(r"^[\s│├└─]*", "", line).split(":")[0] for line in fences[0][1].splitlines()]
    want = [level_id for _, level_id, _, _ in level_list]
    if tree_ids != want:
        problems.append(f"tree lists {tree_ids}, the levels are {want}")
    heads = re.findall(r"^### `([^`]+)`", text, re.M)
    if heads != want:
        problems.append(f"blocks come in the order {heads}, the tree order is {want}")
    blocks = [body for language, body in fences[1:] if language == "mermaid"]
    if len(blocks) != len(want):
        problems.append(f"{len(blocks)} Mermaid blocks for {len(want)} levels")
    for (level, level_id, _, _), source in zip(level_list, blocks):
        for node in level.get("nodes", []):
            node_id = mermaid_id(node.get("id"))
            if not re.search(rf"(^\s*{node_id}[\[\(\{{>]|\bas {node_id}( \{{)?$)", source, re.M):
                problems.append(f"missing node {node.get('id')} in level {level_id}")
        pairs = {}
        for edge in level.get("edges", []):
            pairs[(edge.get("from"), edge.get("to"))] = pairs.get((edge.get("from"), edge.get("to")), 0) + 1
        for (from_id, to_id), count in pairs.items():
            # an edge entering by history ends at a history state inside its target
            target_node = next((candidate for candidate in level.get("nodes", []) if candidate.get("id") == to_id), {})
            target_pattern = "|".join(map(re.escape, [mermaid_id(to_id)] + list(history_states(target_node, level).values())))
            found = len(re.findall(rf"^\s*{mermaid_id(from_id)} (-->|==>|-\.->)(\|.*\|)? ({target_pattern})( : .*)?$", source, re.M))
            if found < count:
                problems.append(f"missing edge {level_id}:{from_id}>{to_id}, {found} of {count} drawn")
    return problems


def constructs():
    """Every construct of the grammar: each property of the document, a level, a node and an edge, each reserved meta
    key and format, and each value of kind, mark, link and gate."""
    node = LEVEL["properties"]["nodes"]["items"]["properties"]
    edge = LEVEL["properties"]["edges"]["items"]["properties"]
    out = [f"document.{property_name}" for property_name in GRAMMAR["properties"]] + [f"level.{property_name}" for property_name in LEVEL["properties"]]
    out += [f"node.{property_name}" for property_name in node] + [f"edge.{property_name}" for property_name in edge]
    out += [f"meta.{k}" for k in RESERVED] + [f"meta.<name>-{format_name}" for format_name in FORMATS]
    out += [f"level.kind={kind}" for kind in KINDS]
    out += [f"node.mark={mark}" for mark in node["mark"]["items"]["enum"]] + [f"edge.mark={mark}" for mark in edge["mark"]["items"]["enum"]]
    out += [f"node.link={link}" for link in node["link"]["enum"]] + [f"node.gate={gate}" for gate in node["gate"]["enum"]]
    return out


def owners(document, where):
    if where == "document":
        return [document]
    level_list = [level for level, _, _, _ in levels(document)]
    if where == "level":
        return level_list
    if where in ("node", "edge"):
        return [element for level in level_list for element in level.get(where + "s", []) if isinstance(element, dict)]
    return [metadata for holder in [document] + level_list + [element for level in level_list for element in level.get("nodes", []) + level.get("edges", [])]
            for metadata in [holder.get("meta")] if isinstance(metadata, dict)]


def other(value):
    if isinstance(value, bool):
        return not value
    if isinstance(value, (int, float)):
        return value + 7
    if isinstance(value, str):
        return value + "zq"
    if isinstance(value, list) and value and all(isinstance(item, str) for item in value):
        return [item + "zq" for item in value]
    if isinstance(value, list) and value:
        return value[1:]
    return None


def mutate(document, construct):
    """A copy of doc with each occurrence of the construct changed, or None when doc holds none."""
    document = copy.deepcopy(document)
    where, _, rest = construct.partition(".")
    property_name, _, value = rest.partition("=")
    hit = False
    for owner in owners(document, where):
        keys = [k for k in owner if k == property_name or (property_name.startswith("<name>-") and k.endswith(property_name[6:]) and k not in RESERVED)]
        for k in keys:
            current = owner[k]
            if value:
                enumeration = KINDS if property_name == "kind" else [item for item in (["happy", "failure", "optional", "unsure"] if property_name == "mark"
                                                                 else ["view", "nest"] if property_name == "link" else ["fork", "join"])]
                swap = enumeration[(enumeration.index(value) + 1) % len(enumeration)]
                if current == value:
                    owner[k], hit = swap, True
                elif isinstance(current, list) and value in current:
                    owner[k], hit = [swap if item == value else item for item in current], True
            elif isinstance(current, dict):
                del owner[k]
                hit = True
            elif other(current) is not None:
                owner[k], hit = other(current), True
    return document if hit else None


def samples():
    """Fixtures the schema checker accepts, then the examples: where a construct is first looked for."""
    checker = SCHEMA_FOLDER / "scripts" / "check-schema.py"
    out = []
    for path in sorted((SCHEMA_FOLDER / "fixtures").glob("*.json")):
        if subprocess.run([sys.executable, str(checker), "check", str(path)], capture_output=True).returncode == 0:
            out.append(path)
    return out + sorted((INTERFACE_FOLDER.parent.parent / "examples").glob("*/schema.json"))


def table_rows(path, width):
    rows = {}
    for line in pathlib.Path(path).read_text().splitlines():
        cells = [field.strip() for field in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if len(cells) >= width and re.fullmatch(r"`[^`]+`", cells[0]):
            rows.setdefault(cells[0].strip("`"), []).append(cells[1:])
    return rows


def losses(document_path):
    rows = table_rows(document_path, 3)
    names = constructs()
    missing = [name for name in names if name not in rows]
    documents = [(path, json.loads(path.read_text())) for path in samples()]
    unshown = []
    for construct in names:
        if construct not in rows or rows[construct][0][0] != "kept":
            continue
        for path, document in documents:
            changed = mutate(document, construct)
            if changed is not None:
                if emit(changed)[0] == emit(document)[0]:
                    unshown.append((construct, f"changing it in {path.parent.name}/{path.name} leaves the output the same"))
                break
        else:
            unshown.append((construct, "no fixture or example holds it to try"))
    for construct in missing:
        print(f"missing: {construct} has no row in the loss table")
    for construct, why in unshown:
        print(f"not shown: {construct} is marked kept, but {why}")
    print("constructs: each property of the document, a level, a node and an edge, each reserved meta key and format, "
          "and each value of kind, mark, link and gate")
    print(f"losses: {len(names)} constructs, {len(missing)} missing from {pathlib.Path(document_path).name}, "
          f"{len(unshown)} kept but not shown")
    return 1 if missing or unshown else 0


def formats(document_path):
    rows = table_rows(document_path, 2)
    want = FORMATS + RESERVED
    problems = [f"missing {k}" for k in want if k not in rows]
    problems += [f"{len(rows[k])} rows for {k}" for k in want if len(rows.get(k, [])) > 1]
    problems += [f"unknown row {k}" for k in rows if k not in want]
    problems += [f"no display in the emitter for {k}" for k in want if k not in SHOW_FORMAT and k not in SHOW_RESERVED]
    print("formats: " + ("; ".join(problems) if problems else "ok"))
    return 1 if problems else 0


def read(path):
    try:
        return json.loads(pathlib.Path(path).read_text())
    except (OSError, ValueError) as e:
        sys.exit(print(f"emit-mermaid: {path}: {e}", file=sys.stderr) or 2)


def main(args):
    options, rest = {}, []
    while args:
        if args[0] == "--check":
            options["check"], args = True, args[1:]
        elif args[0] in ("--split", "--output", "--doc") and len(args) > 1:
            options[args[0][2:]], args = args[1], args[2:]
        else:
            rest, args = rest + args[:1], args[1:]
    args = rest
    if args == ["losses"]:
        return losses(options.get("doc", INTERFACE_FOLDER / "mermaid.md"))
    if args == ["formats"]:
        return formats(options.get("doc", INTERFACE_FOLDER / "formats.md"))
    if len(args) != 1 or args[0].startswith("--"):
        print(__doc__, file=sys.stderr)
        return 2
    document = read(args[0])
    text, blocks = emit(document)
    if options.get("check"):
        problems = check(document, pathlib.Path(options["output"]).read_text() if "output" in options else text)
        print("\n".join(problems + ["ok" if not problems else f"problems: {len(problems)}"]))
        return 1 if problems else 0
    if "split" in options:
        folder = pathlib.Path(options["split"])
        folder.mkdir(parents=True, exist_ok=True)
        for i, (level_id, source) in enumerate(blocks):
            (folder / f"{i:02d}-{level_id}.mmd").write_text(source + "\n")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""zoom: draw a Schema document (../../schema/assets/schema.json) as Markdown with Mermaid, for chat.

  emit-mermaid.py doc.json                        print the levels as a file tree, then one Mermaid block per level,
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
UI = HERE.parent
SCHEMA_DIR = UI.parent / "schema"
GRAMMAR = json.loads((SCHEMA_DIR / "assets" / "schema.json").read_text())
LEVEL = GRAMMAR["$defs"]["level"]
FORMATS = list(GRAMMAR["$defs"]["format"])
RESERVED = list(GRAMMAR["$defs"]["meta"]["properties"])
KINDS = LEVEL["properties"]["kind"]["enum"]
DIFF_SIGN = {"added": "+", "removed": "−", "changed": "~"}
DIFF_TINT = {"added": "#2a7", "removed": "#c33", "changed": "#c90"}


def num(v):
    return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)


def pointer(p):
    return f"[{p}]({p})" if re.match(r"https?://", p) else f"`{p}`"


# one display per format and reserved key; formats.md documents each, `formats` holds the two equal
SHOW_FORMAT = {
    "text": lambda name, v: v,
    "number": lambda name, v: num(v),
    "url": lambda name, v: f"[{name}]({v})",
    "ms": lambda name, v: f"{num(v)} ms",
    "percent": lambda name, v: f"{num(v)}%",
    "date": lambda name, v: v,
    "bool": lambda name, v: "yes" if v else "no",
}
SHOW_RESERVED = {
    "note": lambda v: f"_{v}_",
    "diff": lambda v: f"{DIFF_SIGN.get(v, '?')} {v}",
    "evidence": lambda v: ", ".join(pointer(p) for p in v),
    "constraint": lambda v: ", ".join(f"`{c}`" for c in v),
}


def show_meta(meta):
    out = []
    for k, v in meta.items():
        if k in SHOW_RESERVED:
            out.append(f"{k}: {SHOW_RESERVED[k](v)}")
            continue
        name, _, fmt = k.rpartition("-")
        out.append(f"{name}: {SHOW_FORMAT[fmt](name, v)}" if fmt in SHOW_FORMAT else f"{k}: {v}")
    return "; ".join(out)


def levels(doc):
    """Every level root first, as (level, id, depth, opener node): a level's id is its opener's id, or root."""
    out = []

    def visit(L, lid, depth, opener):
        out.append((L, lid, depth, opener))
        for n in L.get("nodes", []):
            if isinstance(n.get("opens"), dict):
                visit(n["opens"], n.get("id", "?"), depth + 1, n)
    if isinstance(doc.get("level"), dict):
        visit(doc["level"], "root", 0, None)
    return out


def mid(x):
    return "n_" + str(x).replace("-", "_")


def ends(x):
    # a port may join several nodes: one line per node
    return x if isinstance(x, list) else [x]


def quote(text):
    return '"' + str(text).replace('"', "#quot;").replace("<", "#lt;").replace(">", "#gt;") + '"'


def plain(text):
    # stateDiagram labels take no entities: keep them to characters its parser reads as text
    return re.sub(r"[\"{}:;]", "'", str(text)).replace("\n", " ")


def qty(q):
    return f"{num(q['value'])}{(' ' + q['unit']) if q.get('unit') else ''} ({q['kind']})" if isinstance(q, dict) else ""


def node_text(n):
    text = n.get("label", n.get("id", "?"))
    if isinstance(n.get("opens"), dict):
        text += " ▸"
    return text


def edge_text(e):
    marks = e.get("mark", [])
    text = ("✗ " if "failure" in marks else "") + ("? " if "unsure" in marks else "") + e.get("label", "")
    return text + (f" · {qty(e['qty'])}" if e.get("qty") else "")


CLASSES = [
    "classDef happy stroke:#2a7,stroke-width:3px",
    "classDef failure stroke:#c33,stroke-width:2px",
    "classDef optional stroke-dasharray:4 3",
    "classDef unsure stroke:#999,stroke-dasharray:2 2",
    "classDef diffadded fill:#dfd,stroke:#2a7",
    "classDef diffremoved fill:#fdd,stroke:#c33,stroke-dasharray:4 3",
    "classDef diffchanged fill:#ffe9b3,stroke:#c90",
]


def classes(n):
    out = list(n.get("mark", []))
    if isinstance(n.get("meta"), dict) and n["meta"].get("diff") in DIFF_SIGN:
        out.append("diff" + n["meta"]["diff"])
    return out


def flowchart(L):
    kind = L.get("kind")
    lines = ["flowchart " + ("TB" if kind == "topology" else "LR")]
    links = 0
    styles = []

    def shape(n):
        t = quote(node_text(n) + (f"<br/>{qty(n['qty'])}" if n.get("qty") else ""))
        if n.get("gate"):
            return f"{{{{{quote(node_text(n) + ' (' + n['gate'] + ')')}}}}}"
        if kind == "workflow":
            return f"({t})"
        if n.get("abstract"):
            return f"[/{t}/]"
        if n.get("singleton"):
            return f"[[{t}]]"
        return f"[{t}]"

    nodes = L.get("nodes", [])
    parts = [p for p in L.get("partitions", []) if isinstance(p, dict)]
    placed = set()
    for p in parts:
        inside = [n for n in nodes if n.get("partition") == p.get("id")]
        lines.append(f"  subgraph p_{mid(p.get('id'))[2:]}[{quote(p.get('label', p.get('id')))}]")
        lines += [f"    {mid(n.get('id'))}{shape(n)}" for n in inside]
        lines.append("  end")
        placed |= {id(n) for n in inside}
    lines += [f"  {mid(n.get('id'))}{shape(n)}" for n in nodes if id(n) not in placed]
    for i, t in enumerate(L.get("triggers", [])):
        every = f" every {t['every']}" if t.get("every") else ""
        lines.append(f"  t_{i}((\" \")) -->|{quote(t.get('label', '') + every)}| {mid(t.get('to'))}")
        links += 1
    for i, p in enumerate(L.get("in", [])):
        for to in ends(p.get("to")):
            lines.append(f"  in_{i}>{quote(p.get('edge'))}] --> {mid(to)}")
            links += 1
    for i, p in enumerate(L.get("out", [])):
        for frm in ends(p.get("from")):
            lines.append(f"  {mid(frm)} --> out_{i}>{quote(p.get('edge'))}]")
            links += 1
    for e in L.get("edges", []):
        marks = e.get("mark", [])
        arrow = "==>" if "happy" in marks else "-.->" if set(marks) & {"failure", "optional", "unsure"} else "-->"
        label = edge_text(e)
        lines.append(f"  {mid(e.get('from'))} {arrow}{('|' + quote(label) + '|') if label else ''} {mid(e.get('to'))}")
        diff = e.get("meta", {}).get("diff") if isinstance(e.get("meta"), dict) else None
        if diff in DIFF_TINT:
            styles.append(f"  linkStyle {links} stroke:{DIFF_TINT[diff]},stroke-width:3px")
        elif "failure" in marks:
            styles.append(f"  linkStyle {links} stroke:#c33")
        links += 1
    return lines + styles


def state_diagram(L):
    lines = ["stateDiagram-v2", "  direction LR"]
    nodes = L.get("nodes", [])
    regions = [r for r in L.get("regions", []) if isinstance(r, dict)]
    initial = L.get("initial", [])
    initial = [initial] if isinstance(initial, str) else list(initial)
    triggered = {t.get("to") for t in L.get("triggers", [])}
    # an edge is drawn inside its region's block when both ends sit in it, else at the top
    group = {n.get("id"): (n.get("region") if regions else None) for n in nodes}

    def body(members, pad):
        ids = {n.get("id") for n in members}
        out = [f"{pad}state \"{plain(node_text(n) + (' · ' + qty(n['qty']) if n.get('qty') else ''))}\" as {mid(n.get('id'))}"
               for n in members]
        out += [f"{pad}[*] --> {mid(s)}" for s in initial if s in ids and s not in triggered]
        out += [f"{pad}[*] --> {mid(t.get('to'))} : {plain(t.get('label', ''))}"
                for t in L.get("triggers", []) if t.get("to") in ids]
        out += [f"{pad}{mid(e.get('from'))} --> {mid(e.get('to'))}" + (f" : {plain(edge_text(e))}" if edge_text(e) else "")
                for e in L.get("edges", []) if e.get("from") in ids and e.get("to") in ids]
        return out

    if regions:
        lines.append(f"  state \"{plain(L.get('subject') or L.get('title', 'regions'))}\" as regions {{")
        for i, r in enumerate(regions):
            if i:
                lines.append("    --")
            lines.append(f"    state \"{plain(r.get('label', r.get('id')))}\" as r_{mid(r.get('id'))[2:]} {{")
            lines += body([n for n in nodes if n.get("region") == r.get("id")], "      ")
            lines.append("    }")
        lines.append("  }")
    lines += body([n for n in nodes if group.get(n.get("id")) is None], "  ")
    for e in L.get("edges", []):
        a, b = e.get("from"), e.get("to")
        if a not in group or b not in group or group[a] != group[b]:
            lines.append(f"  {mid(e.get('from'))} --> {mid(e.get('to'))}" + (f" : {plain(edge_text(e))}" if edge_text(e) else ""))
    for p in L.get("in", []):
        lines += [f"  [*] --> {mid(to)} : {plain(p.get('edge'))}" for to in ends(p.get("to"))]
    for p in L.get("out", []):
        lines += [f"  {mid(frm)} --> [*] : {plain(p.get('edge'))}" for frm in ends(p.get("from"))]
    return lines


def mermaid(L):
    lines = state_diagram(L) if L.get("kind") == "state" else flowchart(L)
    used = sorted({c for n in L.get("nodes", []) for c in classes(n)})
    lines += [f"  {c}" for c in CLASSES if c.split()[1] in used]
    for c in used:
        members = [mid(n.get("id")) for n in L.get("nodes", []) if c in classes(n)]
        lines.append(f"  class {','.join(members)} {c}")
    return "\n".join(lines)


def tree(doc):
    out = []

    def visit(L, lid, opener, lead, last, top):
        link = f", {opener['link']}" if opener and opener.get("link") else ""
        out.append(("" if top else lead + ("└── " if last else "├── ")) + f"{lid}: {L.get('title', '')} ({L.get('kind')}{link})")
        kids = [n for n in L.get("nodes", []) if isinstance(n.get("opens"), dict)]
        for i, n in enumerate(kids):
            visit(n["opens"], n.get("id", "?"), n, "" if top else lead + ("    " if last else "│   "), i == len(kids) - 1, False)
    if isinstance(doc.get("level"), dict):
        visit(doc["level"], "root", None, "", True, True)
    return out


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def meta_table(L):
    rows = []
    if isinstance(L.get("meta"), dict):
        rows.append(("this level", L["meta"]))
    rows += [(f"`{n.get('id')}` {n.get('label', '')}", n["meta"]) for n in L.get("nodes", []) if isinstance(n.get("meta"), dict)]
    rows += [(f"`{e.get('from')}` → `{e.get('to')}` {e.get('label', '')}", e["meta"])
             for e in L.get("edges", []) if isinstance(e.get("meta"), dict)]
    if not rows:
        return []
    return ["", "| element | metadata |", "| --- | --- |"] + [f"| {cell(a)} | {cell(show_meta(m))} |" for a, m in rows]


def syncs(L):
    return [""] + [f"- sync `{s.get('name')}`: on `{s.get('when')}`" + (f" while `{s['where']}`" if s.get("where") else "")
                   + f", then `{s.get('then')}`" for s in L.get("syncs", [])] if L.get("syncs") else []


def emit(doc):
    """The Markdown for a document, and each level's (id, Mermaid source) in tree order."""
    out = [f"## {doc.get('title', 'Schema')}"]
    if isinstance(doc.get("meta"), dict):
        out += ["", show_meta(doc["meta"])]
    out += ["", "```text", *tree(doc), "```"]
    blocks = []
    for L, lid, depth, opener in levels(doc):
        src = mermaid(L)
        blocks.append((lid, src))
        of = f" of {L['subject']}" if L.get("kind") == "state" and L.get("subject") else ""
        out += ["", f"### `{lid}` {L.get('title', '')} ({L.get('kind')}{of})"]
        if L.get("why"):
            out += ["", f"_{L['why']}_"]
        out += ["", "```mermaid", src, "```"] + syncs(L) + meta_table(L)
    return "\n".join(out) + "\n", blocks


def check(doc, text):
    problems = []
    fences = re.findall(r"^```(\w*)\n(.*?)^```$", text, re.S | re.M)
    lvls = levels(doc)
    if not fences or fences[0][0] != "text":
        return ["the output does not open with a text block of the level tree"]
    tree_ids = [re.sub(r"^[\s│├└─]*", "", line).split(":")[0] for line in fences[0][1].splitlines()]
    want = [lid for _, lid, _, _ in lvls]
    if tree_ids != want:
        problems.append(f"tree lists {tree_ids}, the levels are {want}")
    heads = re.findall(r"^### `([^`]+)`", text, re.M)
    if heads != want:
        problems.append(f"blocks come in the order {heads}, the tree order is {want}")
    blocks = [body for lang, body in fences[1:] if lang == "mermaid"]
    if len(blocks) != len(want):
        problems.append(f"{len(blocks)} Mermaid blocks for {len(want)} levels")
    for (L, lid, _, _), src in zip(lvls, blocks):
        for n in L.get("nodes", []):
            m = mid(n.get("id"))
            if not re.search(rf"(^\s*{m}[\[\(\{{>]|\bas {m}$)", src, re.M):
                problems.append(f"missing node {n.get('id')} in level {lid}")
        pairs = {}
        for e in L.get("edges", []):
            pairs[(e.get("from"), e.get("to"))] = pairs.get((e.get("from"), e.get("to")), 0) + 1
        for (a, b), count in pairs.items():
            found = len(re.findall(rf"^\s*{mid(a)} (-->|==>|-\.->)(\|.*\|)? {mid(b)}( : .*)?$", src, re.M))
            if found < count:
                problems.append(f"missing edge {lid}:{a}>{b}, {found} of {count} drawn")
    return problems


def constructs():
    """Every construct of the grammar: each property of the document, a level, a node and an edge, each reserved meta
    key and format, and each value of kind, mark, link and gate."""
    node = LEVEL["properties"]["nodes"]["items"]["properties"]
    edge = LEVEL["properties"]["edges"]["items"]["properties"]
    out = [f"document.{p}" for p in GRAMMAR["properties"]] + [f"level.{p}" for p in LEVEL["properties"]]
    out += [f"node.{p}" for p in node] + [f"edge.{p}" for p in edge]
    out += [f"meta.{k}" for k in RESERVED] + [f"meta.<name>-{f}" for f in FORMATS]
    out += [f"level.kind={v}" for v in KINDS]
    out += [f"node.mark={v}" for v in node["mark"]["items"]["enum"]] + [f"edge.mark={v}" for v in edge["mark"]["items"]["enum"]]
    out += [f"node.link={v}" for v in node["link"]["enum"]] + [f"node.gate={v}" for v in node["gate"]["enum"]]
    return out


def owners(doc, where):
    if where == "document":
        return [doc]
    lv = [L for L, _, _, _ in levels(doc)]
    if where == "level":
        return lv
    if where in ("node", "edge"):
        return [x for L in lv for x in L.get(where + "s", []) if isinstance(x, dict)]
    return [m for x in [doc] + lv + [y for L in lv for y in L.get("nodes", []) + L.get("edges", [])]
            for m in [x.get("meta")] if isinstance(m, dict)]


def other(v):
    if isinstance(v, bool):
        return not v
    if isinstance(v, (int, float)):
        return v + 7
    if isinstance(v, str):
        return v + "zq"
    if isinstance(v, list) and v and all(isinstance(x, str) for x in v):
        return [x + "zq" for x in v]
    if isinstance(v, list) and v:
        return v[1:]
    return None


def mutate(doc, construct):
    """A copy of doc with each occurrence of the construct changed, or None when doc holds none."""
    doc = copy.deepcopy(doc)
    where, _, rest = construct.partition(".")
    prop, _, value = rest.partition("=")
    hit = False
    for owner in owners(doc, where):
        keys = [k for k in owner if k == prop or (prop.startswith("<name>-") and k.endswith(prop[6:]) and k not in RESERVED)]
        for k in keys:
            v = owner[k]
            if value:
                enum = KINDS if prop == "kind" else [x for x in (["happy", "failure", "optional", "unsure"] if prop == "mark"
                                                                 else ["view", "nest"] if prop == "link" else ["fork", "join"])]
                swap = enum[(enum.index(value) + 1) % len(enum)]
                if v == value:
                    owner[k], hit = swap, True
                elif isinstance(v, list) and value in v:
                    owner[k], hit = [swap if x == value else x for x in v], True
            elif isinstance(v, dict):
                del owner[k]
                hit = True
            elif other(v) is not None:
                owner[k], hit = other(v), True
    return doc if hit else None


def samples():
    """Fixtures the schema checker accepts, then the examples: where a construct is first looked for."""
    checker = SCHEMA_DIR / "scripts" / "check-schema.py"
    out = []
    for f in sorted((SCHEMA_DIR / "fixtures").glob("*.json")):
        if subprocess.run([sys.executable, str(checker), "check", str(f)], capture_output=True).returncode == 0:
            out.append(f)
    return out + sorted((UI.parent.parent / "examples").glob("*/schema.json"))


def table_rows(path, width):
    rows = {}
    for line in pathlib.Path(path).read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if len(cells) >= width and re.fullmatch(r"`[^`]+`", cells[0]):
            rows.setdefault(cells[0].strip("`"), []).append(cells[1:])
    return rows


def losses(doc_path):
    rows = table_rows(doc_path, 3)
    names = constructs()
    missing = [c for c in names if c not in rows]
    docs = [(f, json.loads(f.read_text())) for f in samples()]
    unshown = []
    for c in names:
        if c not in rows or rows[c][0][0] != "kept":
            continue
        for f, d in docs:
            changed = mutate(d, c)
            if changed is not None:
                if emit(changed)[0] == emit(d)[0]:
                    unshown.append((c, f"changing it in {f.parent.name}/{f.name} leaves the output the same"))
                break
        else:
            unshown.append((c, "no fixture or example holds it to try"))
    for c in missing:
        print(f"missing: {c} has no row in the loss table")
    for c, why in unshown:
        print(f"not shown: {c} is marked kept, but {why}")
    print("constructs: each property of the document, a level, a node and an edge, each reserved meta key and format, "
          "and each value of kind, mark, link and gate")
    print(f"losses: {len(names)} constructs, {len(missing)} missing from {pathlib.Path(doc_path).name}, "
          f"{len(unshown)} kept but not shown")
    return 1 if missing or unshown else 0


def formats(doc_path):
    rows = table_rows(doc_path, 2)
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
    opt, rest = {}, []
    while args:
        if args[0] == "--check":
            opt["check"], args = True, args[1:]
        elif args[0] in ("--split", "--output", "--doc") and len(args) > 1:
            opt[args[0][2:]], args = args[1], args[2:]
        else:
            rest, args = rest + args[:1], args[1:]
    args = rest
    if args == ["losses"]:
        return losses(opt.get("doc", UI / "mermaid.md"))
    if args == ["formats"]:
        return formats(opt.get("doc", UI / "formats.md"))
    if len(args) != 1:
        print(__doc__)
        return 2
    doc = read(args[0])
    text, blocks = emit(doc)
    if opt.get("check"):
        problems = check(doc, pathlib.Path(opt["output"]).read_text() if "output" in opt else text)
        print("\n".join(problems + ["ok" if not problems else f"problems: {len(problems)}"]))
        return 1 if problems else 0
    if "split" in opt:
        folder = pathlib.Path(opt["split"])
        folder.mkdir(parents=True, exist_ok=True)
        for i, (lid, src) in enumerate(blocks):
            (folder / f"{i:02d}-{lid}.mmd").write_text(src + "\n")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

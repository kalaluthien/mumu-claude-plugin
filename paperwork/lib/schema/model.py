"""Read a Schema document and index it: levels, nodes, edges, triggers, footprints, and the model's own words."""
import datetime
import json
import re

from . import plan as params



# [name](url), or [name](path), [name](path:12), [name](path:12-30) for a file under plan.root
REF = re.compile(r"\[[^\]]+\]\((?:https?://\S+|(?P<path>[^\s():/][^\s():]*)(?::\d+(?:-\d+)?)?)\)")


def ref_path(r):
    """The file a local ref cites, or None for a url."""
    return REF.fullmatch(r.strip()).group("path")


def split_top(text):
    """Split on commas that are not inside brackets."""
    out, depth, cur = [], 0, ""
    for ch in text:
        if ch in "({[":
            depth += 1
        elif ch in ")}]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    return [x.strip() for x in out + [cur] if x.strip()]


def places(step):
    """The nodes a step is at: one node, or the parts of one component level it uses together."""
    at = step.get("place") if isinstance(step, dict) else step
    return at if isinstance(at, list) else [at]


def walk_steps(seq):
    """Every step of a Scenario, forks included, in order."""
    for item in seq:
        if isinstance(item, list):
            for branch in item:
                yield from walk_steps(branch if isinstance(branch, list) else [branch])
        else:
            yield item


def plan(steps):
    """A Scenario's steps as visits, the moment of each, and the links between them. Steps run in order; a list
    among them forks into branches that run side by side and join at the next step (a branch: one step, a list of
    steps, or [] for going straight to the join). A step at several parts visits them in that moment, in order."""
    nodes, times, links, owner = [], [], [], []
    count = iter(range(10 ** 6))

    def step(item, prev, t):
        if isinstance(item, list):   # a fork: every branch starts after prev; the next step joins their ends
            ends, end = [], t
            for br in item:
                last, bt = step(br, prev, t) if not isinstance(br, list) else seq(br, prev, t)
                ends += [x for x in last if x not in ends]
                end = max(end, bt)
            return ends, end
        k = next(count)
        for x in places(item):
            nodes.append(x)
            times.append(t)
            owner.append(k)
            links.extend((p, len(nodes) - 1) for p in prev)
            prev = [len(nodes) - 1]
        return prev, t + 1

    def seq(items, prev, t):
        for item in items:
            prev, t = step(item, prev, t)
        return prev, t

    seq(steps, [], 0)
    return nodes, times, links, owner


def trig_key(level_id, t):
    return f'{level_id}:@>{t["to"]}#{t["label"]}'


def levels_of(data):
    """Every level, root first, as (level, the id of the node that opens it): the root is the model's `level`, and
    a node's `opens` is the level drawn inside it. A level's id is its opener's id, or root."""
    out = []

    def visit(level, opener):
        out.append((level, opener))
        for n in level.get("nodes", []):
            if isinstance(n, dict) and isinstance(n.get("opens"), dict):
                visit(n["opens"], n.get("id"))
    if isinstance(data.get("level"), dict):
        visit(data["level"], None)
    return out


def flat(data):
    """The model with its levels as one list, each a copy with `id` and `parent` (as the page and the checks read
    it); nodes keep no copy of the level they open."""
    if "levels" in data and "level" not in data:   # already flat
        return data
    levels = []
    for level, opener in levels_of(data):
        L2 = dict(level, id=opener or "root", parent=opener)
        L2["nodes"] = [{k: v for k, v in n.items() if k != "opens"} for n in level.get("nodes", [])]
        if "regions" in L2:   # a state level's regions are its partitions everywhere after this
            L2["partitions"] = L2.pop("regions")
            for n in L2["nodes"]:
                if "region" in n:
                    n["partition"] = n.pop("region")
        levels.append(L2)
    return dict({k: v for k, v in data.items() if k != "level"}, levels=levels, root="root")


def parse(data):
    """Every reference resolved once, before any check reads the model: what each one fails to point at, and the
    few things the schema cannot say. Nothing after this needs to ask whether an id exists."""
    m, out = flat(data), []
    for level, opener in levels_of(data):
        lid = opener or "root"
        if level.get("kind") == "state" and (level.get("partitions") or any("partition" in n for n in level.get("nodes", []))):
            out.append(("form", f"{lid}: a state level's parts are regions (regions, region), not partitions"))
        if level.get("kind") != "state" and (level.get("regions") or any("region" in n for n in level.get("nodes", []))):
            out.append(("form", f"{lid}: only a state level has regions; use partitions"))
    nodes, kind = {}, {}
    for level in m["levels"]:
        for n in level["nodes"]:
            if n["id"] in nodes:
                out.append(("unique-names", f'{n["id"]}: node id used twice'))
            nodes[n["id"]], kind[n["id"]] = n, level
    ops = {o["slug"] for o in m["operations"]}
    rules = {r["slug"] for r in m["rules"]}
    for what, names in (("operation", [o["slug"] for o in m["operations"]]), ("rule", [r["slug"] for r in m["rules"]])):
        out += [("unique-names", f"{x}: {what} defined twice") for x in sorted({x for x in names if names.count(x) > 1})]
    by_id = {level["id"]: level for level in m["levels"]}
    for level in m["levels"]:
        lid, ids = level["id"], {n["id"] for n in level["nodes"]}
        events = {e["label"] for e in level["edges"]}
        if level["kind"] == "state":
            inits = [level["initial"]] if isinstance(level.get("initial"), str) else level.get("initial") or []
            if not inits or set(inits) - ids:
                out.append(("region-without-initial", f"{lid}: name its initial state (one per region)"))
        parts = {p["id"] for p in level.get("partitions", [])}
        for n in level["nodes"]:
            if n.get("partition") and n["partition"] not in parts:
                out.append(("reference", f'{n["id"]}: is in no partition {n["partition"]}'))
        for x, where in [(n, n["id"]) for n in level["nodes"]] + [(e, e.get("label", "")) for e in level["edges"]] + [(t, t.get("label", "")) for t in level.get("triggers", [])]:
            out += [("reference", f"{lid}: {where} names no operation {o}") for o in x.get("ops", []) if o not in ops]
            out += [("reference", f"{lid}: {where} names no rule {r}") for r in x.get("rules", []) if r not in rules]

        for x in [level] + level["nodes"] + level["edges"]:
            out += [("reference", f"{lid}: the insight's rule {md.get('rule')} is no operation or rule") for md in x.get("media", [])
                    if md.get("type") == "insight" and md.get("rule") not in ops | rules]
        for e in level["edges"]:
            if e["from"] not in ids or e["to"] not in ids:
                out.append(("reference", f'{lid}: edge {e["label"]} joins nodes of another level'))
            if e.get("is") and e["is"] not in nodes:
                out.append(("reference", f'{lid}: {e["label"]} is no component {e["is"]}'))
        out += [("reference", f'{lid}: trigger {t["label"]} enters no node of this level') for t in level.get("triggers", []) if t["to"] not in ids]
        if level.get("triggers") and level["kind"] == "topology":
            out.append(("form", f"{lid}: triggers enter workflow or state levels"))
        for y in level.get("syncs", []):
            if y["when"] not in events or y["then"] not in events:
                out.append(("sync-unknown-transition", f'{lid}: sync {y["name"]}: when and then name events of this level'))
            if y.get("where") and y["where"] not in ids:
                out.append(("sync-unknown-transition", f'{lid}: sync {y["name"]}: where names a state of this level'))
        parent_level = by_id.get(kind[level["parent"]]["id"]) if level.get("parent") else None
        if level.get("history") and not (level["kind"] == "state" and parent_level and parent_level["kind"] == "state" and parent_level.get("subject") == level.get("subject")):
            out.append(("history-outside-superstate", f"{lid}: only a state level opened from a state of its subject resumes by history"))
        # a level's id is the node that opens it, so by_id of a node is the level inside it
        inside = lambda n: by_id.get(n) if level["kind"] == "state" and by_id.get(n, {}).get("kind") == "state" and by_id[n].get("subject") == level.get("subject") else None
        finals = {n["id"] for n in level["nodes"] if n.get("final")}
        for e in level["edges"]:
            if e.get("enters") and (e["from"] == e["to"] or not inside(e["to"])):
                why = "a self-loop never enters it" if e["from"] == e["to"] else "it opens no state level of its subject"
                out.append(("enters-without-superstate", f'{lid}: {e["label"]} picks how it enters {e["to"]}, but {why}'))
            if e["from"] in finals:
                out.append(("final-with-exit", f'{lid}: {e["label"]} leaves {e["from"]}, a final state'))
            inner_level = inside(e["from"]) if e.get("completion") else None
            if e.get("completion") and not (inner_level and {n.get("partition") or "_" for n in inner_level["nodes"]} == {n.get("partition") or "_" for n in inner_level["nodes"] if n.get("final")}):
                out.append(("completion-without-final", f'{lid}: {e["label"]} completes {e["from"]}, but a region inside it has no final state'))
        if level.get("in") or level.get("out"):
            if not (level["kind"] in ("workflow", "topology") and parent_level and parent_level["kind"] == level["kind"]):
                out.append(("form", f"{lid}: only a workflow or topology opened from one of its kind has ports; bring outside things in as triggers"))
            else:
                handed = {e["label"] for e in parent_level["edges"]} | {t["label"] for t in parent_level.get("triggers", [])}
                for f in level.get("in", []) + level.get("out", []):
                    ends = [f["to"]] if "to" in f else [f["from"]] if isinstance(f["from"], str) else f["from"]
                    if f["edge"] not in handed or set(ends) - ids:
                        out.append(("reference", f'{lid}: port {f["edge"]} names no edge of the parent or no node here'))
    for s in m["scenarios"]:
        for k, st in enumerate(walk_steps(s["walk"])):
            if not isinstance(st, dict):
                out.append(("steps", f'{s["slug"]}: step {k + 1} is an object {{"place", "does", "expects"}}'))
                continue
            out += [("reference", f'{s["slug"]}: step {k + 1} is at no node {x}') for x in places(st) if x not in nodes]
            if st.get("edge") and not any(e["label"] == st["edge"] for level in m["levels"] for e in level["edges"]):
                out.append(("reference", f'{s["slug"]}: step {k + 1} takes no edge {st["edge"]}'))
        if any(len(f) < 2 for f in forks(s["walk"])):
            out.append(("steps", f'{s["slug"]}: a fork lists two or more branches'))
    for it in m["scenarios"] + m["operations"] + m["rules"] + list(nodes.values()):
        out += [("reference", f'{it.get("slug", it.get("id"))}: write refs as [name](url) or [name](path:line), not {r}') for r in it.get("refs", [])
                if not REF.fullmatch(r.strip())]
    return out


def forks(seq):
    """The forks of a Scenario: the lists among its steps, and the forks inside their branches."""
    for x in seq:
        if isinstance(x, list):
            yield x
            for branch in x:
                if isinstance(branch, list):
                    yield from forks(branch)


class Model:
    def __init__(self, data):
        self.parse_problems = parse(data) if "level" in data else []
        data = flat(data)
        self.m = data
        self.levels = {level["id"]: level for level in data["levels"]}
        self.nodes, self.node_level = {}, {}
        for level in data["levels"]:
            for n in level["nodes"]:
                self.nodes[n["id"]] = n
                self.node_level[n["id"]] = level["id"]
        self.child = {level["parent"]: level["id"] for level in data["levels"] if level.get("parent")}
        self.edges = {f'{level["id"]}:{e["from"]}>{e["to"]}#{i}': (level, e) for level in data["levels"] for i, e in enumerate(level["edges"])}
        self.trigs = {trig_key(level["id"], t): (level, t) for level in data["levels"] for t in level.get("triggers", [])}
        self.ops = {o["slug"]: o for o in data["operations"]}
        self.rules = {i["slug"]: i for i in data["rules"]}
        self.kind_of = {n: self.levels[lid]["kind"] for n, lid in self.node_level.items()}
        self.root = next((level["id"] for level in data["levels"] if not level.get("parent")), None)
        self.sigs = self._signatures()
        self.footprint, self.home = self._footprints()
        self.plan = params.effective(data)
        self.strict = set(self.plan["strict"])

    def level_of(self, node_id):
        return self.levels[self.node_level[node_id]]

    def ancestors(self, lid):
        out = []
        while lid:
            out.append(lid)
            p = self.levels[lid].get("parent")
            lid = self.node_level.get(p) if p else None
        return out

    def depth(self, lid):
        return len(self.ancestors(lid)) - 1

    def is_abstract(self, level, node_id):
        return any(n["id"] == node_id and n.get("abstract") for n in level["nodes"])

    def is_level_step(self, a, b):
        return self.child.get(a) == self.node_level.get(b) or self.child.get(b) == self.node_level.get(a)

    def opener(self, lid):
        return next((n for n, c in self.child.items() if c == lid), None)

    def walk(self, s):
        """A Scenario's steps resolved once, for the checks, Alloy and the page alike: items { x, kind, from, to,
        step } (a node for the moment of its step; an edge from the moment after its source to its arrival) and the
        problems found. A step follows one edge in its direction (either way on a component level), named by the
        step's `edge` when two could (on a component level, parts used together use every relation between them); stepping into or out of an opened node takes no edge, and a step may leave
        a level along an edge of the node that opened it, or enter one along an edge into its opener."""
        visits, times, links, owner = plan(s["walk"])
        flat, items, out = list(walk_steps(s["walk"])), [], []
        ok = lambda i: isinstance(visits[i], str) and visits[i] in self.nodes
        for i, x in enumerate(visits):
            if ok(i):
                items.append({"x": x, "kind": "node", "from": times[i], "to": times[i], "step": owner[i]})
        for a, b in links:
            if not (ok(a) and ok(b)):
                continue
            from_visit, to_visit = visits[a], visits[b]
            want = flat[owner[b]].get("edge") if isinstance(flat[owner[b]], dict) else None
            la, lb = self.node_level[from_visit], self.node_level[to_visit]
            pairs = [(from_visit, to_visit)] if la == lb else []
            if la != lb and not self.is_level_step(from_visit, to_visit):   # leave along the opener's edge, or enter along an edge into it
                from_opener, to_opener = self.opener(la), self.opener(lb)
                pairs = [(from_opener, to_visit)] if from_opener and self.node_level.get(from_opener) == lb else [(from_visit, to_opener)] if to_opener and self.node_level.get(to_opener) == la else []
                if not pairs:
                    out.append(f'{s["slug"]}: {from_visit} → {to_visit} is neither an edge nor a step into or out of a level')
            for f, t in pairs:
                level = self.levels[self.node_level[f]]
                fits = [k for k, (LL, e) in self.edges.items() if LL is level and ((e["from"], e["to"]) == (f, t) or (level["kind"] == "topology" and (e["from"], e["to"]) == (t, f)))]
                fits = [k for k in fits if not want or self.edges[k][1].get("label") == want] if len(fits) > 1 or want else fits
                if len(fits) == 1 or (fits and level["kind"] == "topology"):   # parts used together use every relation between them
                    items += [{"x": k, "kind": "edge", "from": times[a] + (owner[a] != owner[b]), "to": times[b], "step": owner[b]} for k in fits]
                elif fits:
                    out.append(f'{s["slug"]}: {f} → {t} could take {", ".join(self.edges[k][1]["label"] for k in fits)}; name one with "edge"')
                elif any((e["from"], e["to"]) == (t, f) for LL, e in self.edges.values() if LL is level):
                    out.append(f'{s["slug"]}: {f} → {t} walks an edge backwards; a step follows edges in their direction')
                else:
                    out.append(f'{s["slug"]}: {f} → {t} is neither an edge nor a step into or out of a level')
        for i, x in enumerate(visits):   # entering a level where a trigger arrives uses that trigger
            if ok(i) and not any(b == i and ok(a) and self.node_level[visits[a]] == self.node_level[x] for a, b in links):
                lid = self.node_level[x]
                items += [{"x": trig_key(lid, t), "kind": "trig", "from": times[i], "to": times[i], "step": owner[i]}
                          for t in self.levels[lid].get("triggers", []) if t["to"] == x]
        return items, out

    def _footprints(self):
        """What each Scenario uses: the nodes, edges and triggers it walks, and the operations and rules on them."""
        fp, home, sits = {}, {}, self.sits()
        self.walks = {}
        for s in self.m["scenarios"]:
            items, problems = self.walk(s)
            self.walks[s["slug"]] = (items, problems)
            f = {(it["kind"], it["x"]) for it in items}
            f |= {(("op" if x in self.ops else "rule"), x) for x, on in sits.items() if on & f}
            fp[s["slug"]] = f
            first = next((it["x"] for it in items if it["kind"] == "node"), None)
            if first:
                home[s["slug"]] = self.node_level[first]
        return fp, home

    def elements(self):
        return ({("op", x) for x in self.ops} | {("rule", x) for x in self.rules} | {("node", x) for x in self.nodes}
                | {("edge", k) for k in self.edges} | {("trig", k) for k in self.trigs})

    def sits(self):
        """Where each operation and rule is placed, as footprint elements."""
        out = {}
        for n in self.nodes.values():
            for x in n.get("ops", []) + n.get("rules", []):
                out.setdefault(x, set()).add(("node", n["id"]))
        for k, (level, e) in self.edges.items():
            for x in e.get("ops", []) + e.get("rules", []):
                out.setdefault(x, set()).add(("edge", k))
        for k, (level, t) in self.trigs.items():
            for x in t.get("ops", []) + t.get("rules", []):
                out.setdefault(x, set()).add(("trig", k))
        return out

    def _signatures(self):
        """slug -> (receiver, parameter names, verb) for well-formed signatures."""
        out = {}
        for o in self.m["operations"]:
            mm = re.fullmatch(rf"({TYPE})\.({MEMBER})", o["slug"])
            ms = re.fullmatch(r"\s*\((.*)\)\s*→\s*(.+)", o.get("sig", ""))
            if not (mm and ms):
                continue
            params = split_top(ms.group(1))
            names = [p.split(":")[0].strip() for p in params if ":" in p]
            out[o["slug"]] = (mm.group(1), names, mm.group(2))
        return out


def dump(data, pad=""):
    """JSON with each value on one line when it fits in 100 columns, so a model reads by its parts."""
    flat = json.dumps(data, ensure_ascii=False)
    if len(pad) + len(flat) <= 100 or not isinstance(data, (dict, list)) or not data:
        return flat
    inner = pad + " "
    items = [f"{json.dumps(k, ensure_ascii=False)}: {dump(v, inner)}" for k, v in data.items()] if isinstance(data, dict) else [dump(v, inner) for v in data]
    o, c = "{}" if isinstance(data, dict) else "[]"
    return o + "\n" + ",\n".join(inner + x for x in items) + "\n" + pad + c


GRAMMAR = __import__("pathlib").Path(__file__).resolve().parents[2] / "skills/zoom/references/schema/assets/schema.json"
SCHEMA = json.loads(GRAMMAR.read_text(encoding="utf-8"))
# the grammar owns each naming pattern; code builds larger expressions from them unanchored instead of copying them
TYPE, MEMBER = (SCHEMA["$defs"][k]["pattern"].strip("^$") for k in ("type-name", "member"))
TYPES = {"string": str, "array": list, "object": dict, "integer": int, "number": (int, float), "boolean": bool, "null": type(None)}


def real_date(text):
    try:
        datetime.date.fromisoformat(text)
        return True
    except ValueError:
        return False


def shape(data, schema=SCHEMA, path="schema", root=None):
    """Where the document departs from the grammar, each as (rule, "path: what is wrong"): the subset of JSON Schema
    the grammar uses ($ref, type, const, enum, pattern, format date, minimum, maximum, required, properties, propertyNames,
    additionalProperties, items). A subschema's `x-rule` names the rule it states; `x-format-of-key` checks a meta
    value against the format its key ends in."""
    root = root or schema
    rule = schema.get("x-rule", "form")
    if "$ref" in schema:
        return shape(data, root["$defs"][schema["$ref"].rsplit("/", 1)[1]], path, root)
    want = schema.get("type")
    if want and not any(isinstance(data, TYPES[t]) and not (t in ("integer", "number") and isinstance(data, bool)) for t in ([want] if isinstance(want, str) else want)):
        return [(rule, f"{path}: {json.dumps(data, ensure_ascii=False)[:40]} should be {want if isinstance(want, str) else ' or '.join(want)}")]
    if "const" in schema and data != schema["const"]:
        return [(rule, f"{path}: should be {json.dumps(schema['const'])}")]
    if "enum" in schema and data not in schema["enum"]:
        return [(rule, f"{path}: is one of {', '.join(map(str, schema['enum']))}")]
    if "pattern" in schema and isinstance(data, str) and not re.search(schema["pattern"], data):
        return [(rule, f"{path}: {data!r} does not match {schema['pattern']}")]
    if schema.get("format") == "date" and isinstance(data, str) and not real_date(data):
        return [(rule, f"{path}: {data!r} is no calendar date")]
    if isinstance(data, (int, float)) and not isinstance(data, bool):
        if data < schema.get("minimum", data) or data > schema.get("maximum", data):
            return [(rule, f"{path}: {data} is out of range")]
    out = []
    if isinstance(data, dict):
        named = schema.get("x-required-rule", {})
        out += [(named.get(k, rule), f"{path}: missing {k}") for k in schema.get("required", []) if k not in data]
        props, names = schema.get("properties", {}), schema.get("propertyNames")
        for k, v in data.items():
            if names and (bad := shape(k, names, f"{path}.{k}", root)):
                out += bad
            elif k in props:
                out += shape(v, props[k], f"{path}.{k}", root)
            elif schema.get("additionalProperties") is False:
                out.append((rule, f"{path}: unknown field {k}"))
            elif isinstance(extra := schema.get("additionalProperties"), dict):
                out += meta_value(k, v, f"{path}.{k}", root) if extra.get("x-format-of-key") else shape(v, extra, f"{path}.{k}", root)
    if isinstance(data, list) and "items" in schema:
        for i, v in enumerate(data):
            out += shape(v, schema["items"], f"{path}[{i}]", root)
    return out


def meta_value(key, value, path, root):
    """A `<name>-<format>` value against its format, the key's last word; an unknown format is a bad key."""
    fmt = key.rsplit("-", 1)[1]
    if fmt not in root["$defs"]["format"]:
        return [("meta-key", f"{path}: {fmt} is no format; formats: {', '.join(root['$defs']['format'])}")]
    return [("meta-format", text.replace(": ", f": as {fmt}, ", 1)) for _, text in shape(value, root["$defs"]["format"][fmt], path, root)]


def load(path):
    with open(path, encoding="utf-8") as f:
        return Model(json.load(f))

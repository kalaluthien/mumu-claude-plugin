"""Read a zoom-diagram model and index it: levels, nodes, edges, triggers, footprints, and the model's own words."""
import json
import re

from . import plan as params



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

    def visit(L, opener):
        out.append((L, opener))
        for n in L.get("nodes", []):
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
    for L, opener in levels_of(data):
        L2 = dict(L, id=opener or "root", parent=opener)
        L2["nodes"] = [{k: v for k, v in n.items() if k != "opens"} for n in L.get("nodes", [])]
        if "regions" in L2:   # a state level's regions are its partitions everywhere after this
            L2["partitions"] = L2.pop("regions")
            for n in L2["nodes"]:
                if "region" in n:
                    n["partition"] = n.pop("region")
        levels.append(L2)
    return dict({k: v for k, v in data.items() if k != "level"}, levels=levels, root="root")


def parse(data, check_names=()):
    """Every reference resolved once, before any check reads the model: what each one fails to point at, and the
    few things the schema cannot say. Nothing after this needs to ask whether an id exists."""
    m, out = flat(data), []
    for L, opener in levels_of(data):
        lid = opener or "root"
        if L.get("kind") == "state" and (L.get("partitions") or any("partition" in n for n in L.get("nodes", []))):
            out.append(f"{lid}: a state level's parts are regions (regions, region), not partitions")
        if L.get("kind") != "state" and (L.get("regions") or any("region" in n for n in L.get("nodes", []))):
            out.append(f"{lid}: only a state level has regions; use partitions")
    nodes, kind = {}, {}
    for L in m["levels"]:
        for n in L["nodes"]:
            if n["id"] in nodes:
                out.append(f'node id {n["id"]} is used twice')
            nodes[n["id"]], kind[n["id"]] = n, L
    ops = {o["slug"] for o in m["operations"]}
    rules = {r["slug"] for r in m["rules"]}
    for what, names in (("operation", [o["slug"] for o in m["operations"]]), ("rule", [r["slug"] for r in m["rules"]])):
        out += [f"{what} {x} is defined twice" for x in sorted({x for x in names if names.count(x) > 1})]
    screens = m.get("screens", {})
    by_id = {L["id"]: L for L in m["levels"]}
    for L in m["levels"]:
        lid, ids = L["id"], {n["id"] for n in L["nodes"]}
        events = {e["label"] for e in L["edges"]}
        if L["kind"] == "state":
            inits = [L["initial"]] if isinstance(L.get("initial"), str) else L.get("initial") or []
            if not inits or set(inits) - ids:
                out.append(f"{lid}: name its initial state (one per region)")
        parts = {p["id"] for p in L.get("partitions", [])}
        for n in L["nodes"]:
            if n.get("partition") and n["partition"] not in parts:
                out.append(f'{lid}: {n["id"]} is in no partition {n["partition"]}')
            ui = n.get("ui")
            if ui and not (ui["screen"] in screens and ui["block"] in {b["id"] for b in screens[ui["screen"]]["blocks"]}):
                out.append(f'{n["id"]}: ui points at no screen block')
        for x, where in [(n, n["id"]) for n in L["nodes"]] + [(e, e.get("label", "")) for e in L["edges"]] + [(t, t.get("label", "")) for t in L.get("triggers", [])]:
            out += [f"{lid}: {where} names no operation {o}" for o in x.get("ops", []) if o not in ops]
            out += [f"{lid}: {where} names no rule {r}" for r in x.get("rules", []) if r not in rules]

        for x in [L] + L["nodes"] + L["edges"]:
            out += [f"{lid}: the insight's rule {md.get('rule')} is no operation or rule" for md in x.get("media", [])
                    if md.get("type") == "insight" and md.get("rule") not in ops | rules]
        for e in L["edges"]:
            if e["from"] not in ids or e["to"] not in ids:
                out.append(f'{lid}: edge {e["label"]} joins nodes of another level')
            if e.get("is") and e["is"] not in nodes:
                out.append(f'{lid}: {e["label"]} is no component {e["is"]}')
        out += [f'{lid}: trigger {t["label"]} enters no node of this level' for t in L.get("triggers", []) if t["to"] not in ids]
        if L.get("triggers") and L["kind"] == "schema":
            out.append(f"{lid}: triggers enter workflow or state levels")
        for y in L.get("syncs", []):
            if y["when"] not in events or y["then"] not in events:
                out.append(f'{lid}: sync {y["name"]}: when and then name events of this level')
            if y.get("where") and y["where"] not in ids:
                out.append(f'{lid}: sync {y["name"]}: where names a state of this level')
        P = by_id.get(kind[L["parent"]]["id"]) if L.get("parent") else None
        if L.get("in") or L.get("out"):
            if not (L["kind"] == "workflow" and P and P["kind"] == "workflow"):
                out.append(f"{lid}: only a workflow opened from an activity has ports; bring outside things in as triggers")
            else:
                handed = {e["label"] for e in P["edges"]} | {t["label"] for t in P.get("triggers", [])}
                for f in L.get("in", []) + L.get("out", []):
                    ends = [f["to"]] if "to" in f else [f["from"]] if isinstance(f["from"], str) else f["from"]
                    if f["edge"] not in handed or set(ends) - ids:
                        out.append(f'{lid}: port {f["edge"]} names no artifact of the parent or no node here')
    for s in m["scenarios"]:
        for k, st in enumerate(walk_steps(s["walk"])):
            if not isinstance(st, dict):
                out.append(f'{s["slug"]}: step {k + 1} is an object {{"place", "does", "expects"}}')
                continue
            out += [f'{s["slug"]}: step {k + 1} is at no node {x}' for x in places(st) if x not in nodes]
            if st.get("edge") and not any(e["label"] == st["edge"] for L in m["levels"] for e in L["edges"]):
                out.append(f'{s["slug"]}: step {k + 1} takes no edge {st["edge"]}')
        if any(len(f) < 2 for f in forks(s["walk"])):
            out.append(f'{s["slug"]}: a fork lists two or more branches')
    for it in m["scenarios"] + m["operations"] + m["rules"] + list(nodes.values()):
        out += [f'{it.get("slug", it.get("id"))}: write refs as [name](url), not {r}' for r in it.get("refs", [])
                if not re.fullmatch(r"\[[^\]]+\]\(https?://\S+\)", r.strip())]
    plan = m.get("plan") or {}
    out += [f"plan: {x} is no node" for x in plan.get("deep", []) + plan.get("shallow", []) if x not in nodes]
    out += [f"plan: strict {c} is no check" for c in plan.get("strict", []) if check_names and c not in check_names]
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
        self.levels = {L["id"]: L for L in data["levels"]}
        self.nodes, self.node_level = {}, {}
        for L in data["levels"]:
            for n in L["nodes"]:
                self.nodes[n["id"]] = n
                self.node_level[n["id"]] = L["id"]
        self.child = {L["parent"]: L["id"] for L in data["levels"] if L.get("parent")}
        self.edges = {f'{L["id"]}:{e["from"]}>{e["to"]}#{i}': (L, e) for L in data["levels"] for i, e in enumerate(L["edges"])}
        self.trigs = {trig_key(L["id"], t): (L, t) for L in data["levels"] for t in L.get("triggers", [])}
        self.ops = {o["slug"]: o for o in data["operations"]}
        self.rules = {i["slug"]: i for i in data["rules"]}
        self.kind_of = {n: self.levels[lid]["kind"] for n, lid in self.node_level.items()}
        self.root = next((L["id"] for L in data["levels"] if not L.get("parent")), None)
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

    def is_abstract(self, L, node_id):
        return any(n["id"] == node_id and n.get("abstract") for n in L["nodes"])

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
            A, B = visits[a], visits[b]
            want = flat[owner[b]].get("edge") if isinstance(flat[owner[b]], dict) else None
            la, lb = self.node_level[A], self.node_level[B]
            pairs = [(A, B)] if la == lb else []
            if la != lb and not self.is_level_step(A, B):   # leave along the opener's edge, or enter along an edge into it
                P, Q = self.opener(la), self.opener(lb)
                pairs = [(P, B)] if P and self.node_level.get(P) == lb else [(A, Q)] if Q and self.node_level.get(Q) == la else []
                if not pairs:
                    out.append(f'{s["slug"]}: {A} → {B} is neither an edge nor a step into or out of a level')
            for f, t in pairs:
                L = self.levels[self.node_level[f]]
                fits = [k for k, (LL, e) in self.edges.items() if LL is L and ((e["from"], e["to"]) == (f, t) or (L["kind"] == "schema" and (e["from"], e["to"]) == (t, f)))]
                fits = [k for k in fits if not want or self.edges[k][1].get("label") == want] if len(fits) > 1 or want else fits
                if len(fits) == 1 or (fits and L["kind"] == "schema"):   # parts used together use every relation between them
                    items += [{"x": k, "kind": "edge", "from": times[a] + (owner[a] != owner[b]), "to": times[b], "step": owner[b]} for k in fits]
                elif fits:
                    out.append(f'{s["slug"]}: {f} → {t} could take {", ".join(self.edges[k][1]["label"] for k in fits)}; name one with "edge"')
                elif any((e["from"], e["to"]) == (t, f) for LL, e in self.edges.values() if LL is L):
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
        for k, (L, e) in self.edges.items():
            for x in e.get("ops", []) + e.get("rules", []):
                out.setdefault(x, set()).add(("edge", k))
        for k, (L, t) in self.trigs.items():
            for x in t.get("ops", []) + t.get("rules", []):
                out.setdefault(x, set()).add(("trig", k))
        return out

    def _signatures(self):
        """slug -> (receiver, parameter names, verb) for well-formed signatures."""
        out = {}
        for o in self.m["operations"]:
            mm = re.fullmatch(r"([A-Z][A-Za-z0-9]*)\.([a-z][A-Za-z0-9]*)", o["slug"])
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


SCHEMA = json.loads((__import__("pathlib").Path(__file__).resolve().parents[2] / "skills/show-me/references/zoom-diagram/assets/model-schema.json").read_text(encoding="utf-8"))
TYPES = {"string": str, "array": list, "object": dict, "integer": int, "number": (int, float), "boolean": bool, "null": type(None)}


def shape(data, schema=SCHEMA, path="model"):
    """Where the file departs from assets/model.schema.json, each as path: what is wrong (a small subset of
    JSON Schema: type, enum, required, properties, additionalProperties, items, $ref)."""
    if "$ref" in schema:
        schema = SCHEMA["definitions"][schema["$ref"].rsplit("/", 1)[1]]
    want = schema.get("type")
    if want and not any(isinstance(data, TYPES[t]) and not (t == "integer" and isinstance(data, bool)) for t in ([want] if isinstance(want, str) else want)):
        return [f"{path}: should be {want if isinstance(want, str) else ' or '.join(want)}"]
    if "enum" in schema and data not in schema["enum"]:
        return [f"{path}: is one of {', '.join(map(str, schema['enum']))}"]
    out = []
    if isinstance(data, dict):
        out += [f"{path}: missing {k}" for k in schema.get("required", []) if k not in data]
        props = schema.get("properties", {})
        for k, v in data.items():
            if k in props:
                out += shape(v, props[k], f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                out.append(f"{path}: unknown field {k}")
    if isinstance(data, list) and "items" in schema:
        for i, v in enumerate(data):
            out += shape(v, schema["items"], f"{path}[{i}]")
    return out


def load(path):
    with open(path, encoding="utf-8") as f:
        return Model(json.load(f))

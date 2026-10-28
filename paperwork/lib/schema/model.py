"""Read a Schema document and index it: levels, nodes, edges, triggers, footprints, and the model's own words."""
import datetime
import json
import re

from . import plan as parameters



# [name](url), or [name](path), [name](path:12), [name](path:12-30) for a file under plan.root
REFERENCE = re.compile(r"\[[^\]]+\]\((?:https?://\S+|(?P<path>[^\s():/][^\s():]*)(?::\d+(?:-\d+)?)?)\)")


def reference_path(reference):
    """The file a local ref cites, or None for a url."""
    return REFERENCE.fullmatch(reference.strip()).group("path")


def split_top(text):
    """Split on commas that are not inside brackets."""
    out, depth, current = [], 0, ""
    for character in text:
        if character in "({[":
            depth += 1
        elif character in ")}]":
            depth -= 1
        if character == "," and depth == 0:
            out.append(current)
            current = ""
        else:
            current += character
    return [part.strip() for part in out + [current] if part.strip()]


def places(step):
    """The nodes a step is at: one node, or the parts of one component level it uses together."""
    at = step.get("place") if isinstance(step, dict) else step
    return at if isinstance(at, list) else [at]


def walk_steps(sequence):
    """Every step of a Scenario, forks included, in order."""
    for item in sequence:
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

    def step(item, previous, moment):
        if isinstance(item, list):   # a fork: every branch starts after prev; the next step joins their ends
            ends, end = [], moment
            for branch in item:
                last, branch_end = step(branch, previous, moment) if not isinstance(branch, list) else sequence(branch, previous, moment)
                ends += [visit for visit in last if visit not in ends]
                end = max(end, branch_end)
            return ends, end
        step_index = next(count)
        for place in places(item):
            nodes.append(place)
            times.append(moment)
            owner.append(step_index)
            links.extend((source, len(nodes) - 1) for source in previous)
            previous = [len(nodes) - 1]
        return previous, moment + 1

    def sequence(items, previous, moment):
        for item in items:
            previous, moment = step(item, previous, moment)
        return previous, moment

    sequence(steps, [], 0)
    return nodes, times, links, owner


def trigger_key(level_id, trigger):
    return f'{level_id}:@>{trigger["to"]}#{trigger["label"]}'


def levels_of(data):
    """Every level, root first, as (level, the id of the node that opens it): the root is the model's `level`, and
    a node's `opens` is the level drawn inside it. A level's id is its opener's id, or root."""
    out = []

    def visit(level, opener):
        out.append((level, opener))
        for node in level.get("nodes", []):
            if isinstance(node, dict) and isinstance(node.get("opens"), dict):
                visit(node["opens"], node.get("id"))
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
        flat_level = dict(level, id=opener or "root", parent=opener)
        flat_level["nodes"] = [{k: value for k, value in node.items() if k != "opens"} for node in level.get("nodes", [])]
        if "regions" in flat_level:   # a state level's regions are its partitions everywhere after this
            flat_level["partitions"] = flat_level.pop("regions")
            for node in flat_level["nodes"]:
                if "region" in node:
                    node["partition"] = node.pop("region")
        levels.append(flat_level)
    return dict({k: value for k, value in data.items() if k != "level"}, levels=levels, root="root")


def parse(data):
    """Every reference resolved once, before any check reads the model: what each one fails to point at, and the
    few things the schema cannot say. Nothing after this needs to ask whether an id exists."""
    document, out = flat(data), []
    for level, opener in levels_of(data):
        level_id = opener or "root"
        if level.get("kind") == "state" and (level.get("partitions") or any("partition" in node for node in level.get("nodes", []))):
            out.append(("form", f"{level_id}: a state level's parts are regions (regions, region), not partitions"))
        if level.get("kind") != "state" and (level.get("regions") or any("region" in node for node in level.get("nodes", []))):
            out.append(("form", f"{level_id}: only a state level has regions; use partitions"))
    nodes, kind = {}, {}
    for level in document["levels"]:
        for node in level["nodes"]:
            if node["id"] in nodes:
                out.append(("unique-names", f'{node["id"]}: node id used twice'))
            nodes[node["id"]], kind[node["id"]] = node, level
    operations = {operation["slug"] for operation in document["operations"]}
    rules = {rule["slug"] for rule in document["rules"]}
    for what, names in (("operation", [operation["slug"] for operation in document["operations"]]), ("rule", [rule["slug"] for rule in document["rules"]])):
        out += [("unique-names", f"{name}: {what} defined twice") for name in sorted({name for name in names if names.count(name) > 1})]
    by_id = {level["id"]: level for level in document["levels"]}
    for level in document["levels"]:
        level_id, ids = level["id"], {node["id"] for node in level["nodes"]}
        events = {edge["label"] for edge in level["edges"]}
        if level["kind"] == "state":
            initial_states = [level["initial"]] if isinstance(level.get("initial"), str) else level.get("initial") or []
            if not initial_states or set(initial_states) - ids:
                out.append(("region-without-initial", f"{level_id}: name its initial state (one per region)"))
        parts = {partition["id"] for partition in level.get("partitions", [])}
        for node in level["nodes"]:
            if node.get("partition") and node["partition"] not in parts:
                out.append(("reference", f'{node["id"]}: is in no partition {node["partition"]}'))
        for element, where in [(node, node["id"]) for node in level["nodes"]] + [(edge, edge.get("label", "")) for edge in level["edges"]] + [(trigger, trigger.get("label", "")) for trigger in level.get("triggers", [])]:
            out += [("reference", f"{level_id}: {where} names no operation {operation}") for operation in element.get("ops", []) if operation not in operations]
            out += [("reference", f"{level_id}: {where} names no rule {rule}") for rule in element.get("rules", []) if rule not in rules]

        for element in [level] + level["nodes"] + level["edges"]:
            out += [("reference", f"{level_id}: the insight's rule {medium.get('rule')} is no operation or rule") for medium in element.get("media", [])
                    if medium.get("type") == "insight" and medium.get("rule") not in operations | rules]
        for edge in level["edges"]:
            if edge["from"] not in ids or edge["to"] not in ids:
                out.append(("reference", f'{level_id}: edge {edge["label"]} joins nodes of another level'))
            if edge.get("is") and edge["is"] not in nodes:
                out.append(("reference", f'{level_id}: {edge["label"]} is no component {edge["is"]}'))
        out += [("reference", f'{level_id}: trigger {trigger["label"]} enters no node of this level') for trigger in level.get("triggers", []) if trigger["to"] not in ids]
        if level.get("triggers") and level["kind"] == "topology":
            out.append(("form", f"{level_id}: triggers enter workflow or state levels"))
        for sync in level.get("syncs", []):
            if sync["when"] not in events or sync["then"] not in events:
                out.append(("sync-unknown-transition", f'{level_id}: sync {sync["name"]}: when and then name events of this level'))
            if sync.get("where") and sync["where"] not in ids:
                out.append(("sync-unknown-transition", f'{level_id}: sync {sync["name"]}: where names a state of this level'))
        parent_level = by_id.get(kind[level["parent"]]["id"]) if level.get("parent") else None
        if level.get("history") and not (level["kind"] == "state" and parent_level and parent_level["kind"] == "state" and parent_level.get("subject") == level.get("subject")):
            out.append(("history-outside-superstate", f"{level_id}: only a state level opened from a state of its subject resumes by history"))
        # a level's id is the node that opens it, so by_id of a node is the level inside it
        inside = lambda node_id: by_id.get(node_id) if level["kind"] == "state" and by_id.get(node_id, {}).get("kind") == "state" and by_id[node_id].get("subject") == level.get("subject") else None
        finals = {node["id"] for node in level["nodes"] if node.get("final")}
        for edge in level["edges"]:
            if edge.get("enters") and (edge["from"] == edge["to"] or not inside(edge["to"])):
                why = "a self-loop never enters it" if edge["from"] == edge["to"] else "it opens no state level of its subject"
                out.append(("enters-without-superstate", f'{level_id}: {edge["label"]} picks how it enters {edge["to"]}, but {why}'))
            if edge["from"] in finals:
                out.append(("final-with-exit", f'{level_id}: {edge["label"]} leaves {edge["from"]}, a final state'))
            inner_level = inside(edge["from"]) if edge.get("completion") else None
            if edge.get("completion") and not (inner_level and {node.get("partition") or "_" for node in inner_level["nodes"]} == {node.get("partition") or "_" for node in inner_level["nodes"] if node.get("final")}):
                out.append(("completion-without-final", f'{level_id}: {edge["label"]} completes {edge["from"]}, but a region inside it has no final state'))
        if level.get("in") or level.get("out"):
            if not (level["kind"] in ("workflow", "topology") and parent_level and parent_level["kind"] == level["kind"]):
                out.append(("form", f"{level_id}: only a workflow or topology opened from one of its kind has ports; bring outside things in as triggers"))
            else:
                handed = {edge["label"] for edge in parent_level["edges"]} | {trigger["label"] for trigger in parent_level.get("triggers", [])}
                for port in level.get("in", []) + level.get("out", []):
                    ends = [port["to"]] if "to" in port else [port["from"]] if isinstance(port["from"], str) else port["from"]
                    if port["edge"] not in handed or set(ends) - ids:
                        out.append(("reference", f'{level_id}: port {port["edge"]} names no edge of the parent or no node here'))
    for scenario in document["scenarios"]:
        for i, step in enumerate(walk_steps(scenario["walk"])):
            if not isinstance(step, dict):
                out.append(("steps", f'{scenario["slug"]}: step {i + 1} is an object {{"place", "does", "expects"}}'))
                continue
            out += [("reference", f'{scenario["slug"]}: step {i + 1} is at no node {place}') for place in places(step) if place not in nodes]
            if step.get("edge") and not any(edge["label"] == step["edge"] for level in document["levels"] for edge in level["edges"]):
                out.append(("reference", f'{scenario["slug"]}: step {i + 1} takes no edge {step["edge"]}'))
        if any(len(fork) < 2 for fork in forks(scenario["walk"])):
            out.append(("steps", f'{scenario["slug"]}: a fork lists two or more branches'))
    for it in document["scenarios"] + document["operations"] + document["rules"] + list(nodes.values()):
        out += [("reference", f'{it.get("slug", it.get("id"))}: write refs as [name](url) or [name](path:line), not {reference}') for reference in it.get("refs", [])
                if not REFERENCE.fullmatch(reference.strip())]
    return out


def forks(sequence):
    """The forks of a Scenario: the lists among its steps, and the forks inside their branches."""
    for item in sequence:
        if isinstance(item, list):
            yield item
            for branch in item:
                if isinstance(branch, list):
                    yield from forks(branch)


class Model:
    def __init__(self, data):
        self.parse_problems = parse(data) if "level" in data else []
        data = flat(data)
        self.document = data
        self.levels = {level["id"]: level for level in data["levels"]}
        self.nodes, self.node_level = {}, {}
        for level in data["levels"]:
            for node in level["nodes"]:
                self.nodes[node["id"]] = node
                self.node_level[node["id"]] = level["id"]
        self.child = {level["parent"]: level["id"] for level in data["levels"] if level.get("parent")}
        self.edges = {f'{level["id"]}:{edge["from"]}>{edge["to"]}#{i}': (level, edge) for level in data["levels"] for i, edge in enumerate(level["edges"])}
        self.triggers = {trigger_key(level["id"], trigger): (level, trigger) for level in data["levels"] for trigger in level.get("triggers", [])}
        self.operations = {operation["slug"]: operation for operation in data["operations"]}
        self.rules = {rule["slug"]: rule for rule in data["rules"]}
        self.kind_of = {node_id: self.levels[level_id]["kind"] for node_id, level_id in self.node_level.items()}
        self.root = next((level["id"] for level in data["levels"] if not level.get("parent")), None)
        self.signatures = self._signatures()
        self.footprint, self.home = self._footprints()
        self.plan = parameters.effective(data)
        self.strict = set(self.plan["strict"])

    def level_of(self, node_id):
        return self.levels[self.node_level[node_id]]

    def ancestors(self, level_id):
        out = []
        while level_id:
            out.append(level_id)
            opener_id = self.levels[level_id].get("parent")
            level_id = self.node_level.get(opener_id) if opener_id else None
        return out

    def depth(self, level_id):
        return len(self.ancestors(level_id)) - 1

    def is_abstract(self, level, node_id):
        return any(node["id"] == node_id and node.get("abstract") for node in level["nodes"])

    def is_level_step(self, first_node, second_node):
        return self.child.get(first_node) == self.node_level.get(second_node) or self.child.get(second_node) == self.node_level.get(first_node)

    def opener(self, level_id):
        return next((node_id for node_id, child_id in self.child.items() if child_id == level_id), None)

    def walk(self, scenario):
        """A Scenario's steps resolved once, for the checks, Alloy and the page alike: items { x, kind, from, to,
        step } (a node for the moment of its step; an edge from the moment after its source to its arrival) and the
        problems found. A step follows one edge in its direction (either way on a component level), named by the
        step's `edge` when two could (on a component level, parts used together use every relation between them); stepping into or out of an opened node takes no edge, and a step may leave
        a level along an edge of the node that opened it, or enter one along an edge into its opener."""
        visits, times, links, owner = plan(scenario["walk"])
        flat, items, out = list(walk_steps(scenario["walk"])), [], []
        ok = lambda i: isinstance(visits[i], str) and visits[i] in self.nodes
        for i, visit in enumerate(visits):
            if ok(i):
                items.append({"x": visit, "kind": "node", "from": times[i], "to": times[i], "step": owner[i]})
        for source_index, target_index in links:
            if not (ok(source_index) and ok(target_index)):
                continue
            from_visit, to_visit = visits[source_index], visits[target_index]
            want = flat[owner[target_index]].get("edge") if isinstance(flat[owner[target_index]], dict) else None
            from_level, to_level = self.node_level[from_visit], self.node_level[to_visit]
            pairs = [(from_visit, to_visit)] if from_level == to_level else []
            if from_level != to_level and not self.is_level_step(from_visit, to_visit):   # leave along the opener's edge, or enter along an edge into it
                from_opener, to_opener = self.opener(from_level), self.opener(to_level)
                pairs = [(from_opener, to_visit)] if from_opener and self.node_level.get(from_opener) == to_level else [(from_visit, to_opener)] if to_opener and self.node_level.get(to_opener) == from_level else []
                if not pairs:
                    out.append(f'{scenario["slug"]}: {from_visit} → {to_visit} is neither an edge nor a step into or out of a level')
            for from_node, to_node in pairs:
                level = self.levels[self.node_level[from_node]]
                fits = [k for k, (edge_level, edge) in self.edges.items() if edge_level is level and ((edge["from"], edge["to"]) == (from_node, to_node) or (level["kind"] == "topology" and (edge["from"], edge["to"]) == (to_node, from_node)))]
                fits = [k for k in fits if not want or self.edges[k][1].get("label") == want] if len(fits) > 1 or want else fits
                if len(fits) == 1 or (fits and level["kind"] == "topology"):   # parts used together use every relation between them
                    items += [{"x": k, "kind": "edge", "from": times[source_index] + (owner[source_index] != owner[target_index]), "to": times[target_index], "step": owner[target_index]} for k in fits]
                elif fits:
                    out.append(f'{scenario["slug"]}: {from_node} → {to_node} could take {", ".join(self.edges[k][1]["label"] for k in fits)}; name one with "edge"')
                elif any((edge["from"], edge["to"]) == (to_node, from_node) for edge_level, edge in self.edges.values() if edge_level is level):
                    out.append(f'{scenario["slug"]}: {from_node} → {to_node} walks an edge backwards; a step follows edges in their direction')
                else:
                    out.append(f'{scenario["slug"]}: {from_node} → {to_node} is neither an edge nor a step into or out of a level')
        for i, visit in enumerate(visits):   # entering a level where a trigger arrives uses that trigger
            if ok(i) and not any(to_index == i and ok(from_index) and self.node_level[visits[from_index]] == self.node_level[visit] for from_index, to_index in links):
                level_id = self.node_level[visit]
                items += [{"x": trigger_key(level_id, trigger), "kind": "trig", "from": times[i], "to": times[i], "step": owner[i]}
                          for trigger in self.levels[level_id].get("triggers", []) if trigger["to"] == visit]
        return items, out

    def _footprints(self):
        """What each Scenario uses: the nodes, edges and triggers it walks, and the operations and rules on them."""
        footprints, home, sits = {}, {}, self.sits()
        self.walks = {}
        for scenario in self.document["scenarios"]:
            items, problems = self.walk(scenario)
            self.walks[scenario["slug"]] = (items, problems)
            footprint = {(it["kind"], it["x"]) for it in items}
            footprint |= {(("op" if slug in self.operations else "rule"), slug) for slug, on in sits.items() if on & footprint}
            footprints[scenario["slug"]] = footprint
            first = next((it["x"] for it in items if it["kind"] == "node"), None)
            if first:
                home[scenario["slug"]] = self.node_level[first]
        return footprints, home

    def elements(self):
        return ({("op", slug) for slug in self.operations} | {("rule", slug) for slug in self.rules} | {("node", node_id) for node_id in self.nodes}
                | {("edge", k) for k in self.edges} | {("trig", k) for k in self.triggers})

    def sits(self):
        """Where each operation and rule is placed, as footprint elements."""
        out = {}
        for node in self.nodes.values():
            for slug in node.get("ops", []) + node.get("rules", []):
                out.setdefault(slug, set()).add(("node", node["id"]))
        for k, (level, edge) in self.edges.items():
            for slug in edge.get("ops", []) + edge.get("rules", []):
                out.setdefault(slug, set()).add(("edge", k))
        for k, (level, trigger) in self.triggers.items():
            for slug in trigger.get("ops", []) + trigger.get("rules", []):
                out.setdefault(slug, set()).add(("trig", k))
        return out

    def _signatures(self):
        """slug -> (receiver, parameter names, verb) for well-formed signatures."""
        out = {}
        for operation in self.document["operations"]:
            slug_match = re.fullmatch(rf"({TYPE})\.({MEMBER})", operation["slug"])
            signature_match = re.fullmatch(r"\s*\((.*)\)\s*→\s*(.+)", operation.get("sig", ""))
            if not (slug_match and signature_match):
                continue
            parameter_texts = split_top(signature_match.group(1))
            names = [parameter.split(":")[0].strip() for parameter in parameter_texts if ":" in parameter]
            out[operation["slug"]] = (slug_match.group(1), names, slug_match.group(2))
        return out


def dump(data, pad=""):
    """JSON with each value on one line when it fits in 100 columns, so a model reads by its parts."""
    flat = json.dumps(data, ensure_ascii=False)
    if len(pad) + len(flat) <= 100 or not isinstance(data, (dict, list)) or not data:
        return flat
    inner = pad + " "
    items = [f"{json.dumps(k, ensure_ascii=False)}: {dump(value, inner)}" for k, value in data.items()] if isinstance(data, dict) else [dump(value, inner) for value in data]
    opening, closing = "{}" if isinstance(data, dict) else "[]"
    return opening + "\n" + ",\n".join(inner + item for item in items) + "\n" + pad + closing


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
    if want and not any(isinstance(data, TYPES[type_name]) and not (type_name in ("integer", "number") and isinstance(data, bool)) for type_name in ([want] if isinstance(want, str) else want)):
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
        properties, names = schema.get("properties", {}), schema.get("propertyNames")
        for k, value in data.items():
            if names and (bad := shape(k, names, f"{path}.{k}", root)):
                out += bad
            elif k in properties:
                out += shape(value, properties[k], f"{path}.{k}", root)
            elif schema.get("additionalProperties") is False:
                out.append((rule, f"{path}: unknown field {k}"))
            elif isinstance(extra := schema.get("additionalProperties"), dict):
                out += meta_value(k, value, f"{path}.{k}", root) if extra.get("x-format-of-key") else shape(value, extra, f"{path}.{k}", root)
    if isinstance(data, list) and "items" in schema:
        for i, value in enumerate(data):
            out += shape(value, schema["items"], f"{path}[{i}]", root)
    return out


def meta_value(key, value, path, root):
    """A `<name>-<format>` value against its format, the key's last word; an unknown format is a bad key."""
    format_name = key.rsplit("-", 1)[1]
    if format_name not in root["$defs"]["format"]:
        return [("meta-key", f"{path}: {format_name} is no format; formats: {', '.join(root['$defs']['format'])}")]
    return [("meta-format", text.replace(": ", f": as {format_name}, ", 1)) for _, text in shape(value, root["$defs"]["format"][format_name], path, root)]


def load(path):
    with open(path, encoding="utf-8") as file:
        return Model(json.load(file))

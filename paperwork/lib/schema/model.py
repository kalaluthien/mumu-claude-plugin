"""Read a Schema document and index it: levels, nodes, edges, and where a Scenario walks."""
import datetime
import json
import pathlib
import re


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
    """The nodes a step is at: one node, or the parts of one level it uses together."""
    return step["place"] if isinstance(step["place"], list) else [step["place"]]


def levels_of(data):
    """Every level, root first, as (level, the id of the node that opens it): the root is the document's `level`, and
    a node's `opens` is the level drawn inside it. A level's id is its opener's id, or root."""
    out = []

    def visit(level, opener):
        out.append((level, opener))
        for node in level["nodes"]:
            if "opens" in node:
                visit(node["opens"], node["id"])
    visit(data["level"], None)
    return out


class Model:
    def __init__(self, data):
        self.document = data
        self.levels, self.parent, self.nodes, self.node_level, self.edges = {}, {}, {}, {}, {}
        for level, opener in levels_of(data):
            level_id = opener or "root"
            self.levels[level_id], self.parent[level_id] = level, opener
            for node in level["nodes"]:
                self.nodes[node["id"]], self.node_level[node["id"]] = node, level_id
            for i, edge in enumerate(level["edges"]):
                self.edges[f'{level_id}:{edge["from"]}>{edge["to"]}#{i}'] = (level_id, edge)
        self.rules = {rule["slug"]: rule for rule in data["rules"]}

    def states(self, level_id):
        """The nodes of a level a transition touches; every other node of it is a part."""
        return {edge[end] for edge in self.levels[level_id]["edges"] if edge["kind"] == "transition" for end in ("from", "to")}

    def sits(self):
        """Where each rule is placed, as ("node", id) and ("edge", key)."""
        out = {}
        for node in self.nodes.values():
            for slug in node.get("rules", []):
                out.setdefault(slug, set()).add(("node", node["id"]))
        for key, (_, edge) in self.edges.items():
            for slug in edge.get("rules", []):
                out.setdefault(slug, set()).add(("edge", key))
        return out

    def between(self, first, second, label):
        """The edges a step from one node to the next takes, and what is wrong with it. Stepping into or out of an
        opened node takes no edge; a step may leave a level along an edge of its opener, or enter along an edge into it."""
        wrong = f"{first} → {second} is neither an edge nor a step into or out of a level"
        from_level, to_level = self.node_level[first], self.node_level[second]
        if from_level != to_level:
            if first == self.parent[to_level] or second == self.parent[from_level]:
                return [], None
            outer, inner = self.parent[from_level], self.parent[to_level]
            if outer and self.node_level[outer] == to_level:
                first = outer
            elif inner and self.node_level[inner] == from_level:
                second = inner
            else:
                return [], wrong
        level_id = self.node_level[first]
        fits = [key for key, (edge_level, edge) in self.edges.items() if edge_level == level_id and (not label or edge["label"] == label)
                and ((edge["from"], edge["to"]) == (first, second) or (edge["kind"] == "call" and (edge["from"], edge["to"]) == (second, first)))]
        if fits and (len(fits) == 1 or all(self.edges[key][1]["kind"] == "call" for key in fits)):   # parts used together use every call between them
            return fits, None
        if fits:
            return [], f'{first} → {second} could take {", ".join(self.edges[key][1]["label"] for key in fits)}; name one with "edge"'
        if any((edge["from"], edge["to"]) == (second, first) for edge_level, edge in self.edges.values() if edge_level == level_id):
            return [], f"{first} → {second} walks a transition backwards"
        return [], wrong

    def walk(self, scenario):
        """A Scenario's steps resolved once, for the check and the page alike: {nodes, edges} per step, and the problems found."""
        steps, problems, previous = [], [], None
        for index, step in enumerate(scenario["walk"]):
            nodes, edges = [], []
            for place in places(step):
                if place not in self.nodes:
                    problems.append(f'{scenario["slug"]}: step {index + 1} is at no node {place}')
                    continue
                if previous:
                    taken, wrong = self.between(previous, place, step.get("edge"))
                    edges += [key for key in taken if key not in edges]
                    problems += [f'{scenario["slug"]}: step {index + 1}: {wrong}'] if wrong else []
                nodes.append(place)
                previous = place
            steps.append({"nodes": nodes, "edges": edges})
        return steps, problems


GRAMMAR = pathlib.Path(__file__).resolve().parents[2] / "skills/zoom/references/schema/assets/schema.json"
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
    additionalProperties, items). A subschema's `x-rule` names the rule it states."""
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
                out += shape(value, extra, f"{path}.{k}", root)
    if isinstance(data, list) and "items" in schema:
        for i, value in enumerate(data):
            out += shape(value, schema["items"], f"{path}[{i}]", root)
    return out

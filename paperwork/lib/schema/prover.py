"""The model in Alloy 6: the names it declares, its translation to a module, and running that module.

Translation is deterministic. Components, outside types and artifacts become signatures; attributes become
fields; states become mutable subsets of the level's subject; a workflow becomes a singleton run whose
`at` holds the active steps. Every operation call, event and trigger is reified as a Call atom, so
"x.verb happened" is a predicate on the calls of the current step (Practical Alloy's event idiom).
Formulas are already Alloy and are copied as written.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import formula
from .model import MEMBER, TYPE, split_top

PRIMITIVE_SIGNATURES = {"Text", "Url", "Date"}
PRIMITIVE_INTEGERS = {"Number", "Count", "Int"}
JAR_URL = "https://github.com/AlloyTools/org.alloytools.alloy/releases/download/v6.2.0/org.alloytools.alloy.dist.jar"
JAR_SHA256 = "6b8c1cb5bc93bedfc7c61435c4e1ab6e688a242dc702a394628d9a9801edb78d"   # of the v6.2.0 jar


def identifier(label):
    """UpperCamel name of a label: 'Pull request' → PullRequest, 'MCP tool' → MCPTool."""
    return "".join(word[0].upper() + word[1:] for word in re.findall(r"[A-Za-z0-9]+", label))


def lower(label):
    """lowerCamel name: 'mark ready' → markReady, 'fast-forward-push' → fastForwardPush."""
    words = re.findall(r"[A-Za-z0-9]+", label)
    return (words[0][0].lower() + words[0][1:] + "".join(word[0].upper() + word[1:] for word in words[1:])) if words else ""


def singular(name):
    for end, cut in (("ies", "y"), ("ses", "s"), ("s", "")):
        if name.endswith(end) and not name.endswith("ss"):
            return name[: len(name) - len(end)] + cut
    return name


def artifact_types(label):
    """Type names an artifact label stands for: every tail of its words, singular or as written."""
    if re.fullmatch(r"[\w-]+\.[a-z]+", label.strip()):   # a file stands for what it holds: model.json is a Model
        label = label.rsplit(".", 1)[0]
    words = re.findall(r"[A-Za-z0-9]+", label)
    out = set()
    for i in range(len(words)):
        type_name = identifier(" ".join(words[i:]))
        out |= {type_name, singular(type_name)}
    return out


class Type:
    """A type expression: names (a union), an enum literal set, or a tuple; with a multiplicity."""

    def __init__(self, text):
        self.text = remainder = text.strip()
        self.multiplicity = "one"
        for end, multiplicity in (("[1..]", "some"), ("[]", "set"), ("?", "lone")):
            if remainder.endswith(end):
                self.multiplicity, remainder = multiplicity, remainder[: -len(end)].strip()
                break
        self.names, self.atoms, self.tuple = [], None, None
        if remainder.startswith("(") and remainder.endswith(")"):
            inner = remainder[1:-1]
            parts = split_top(inner)
            if len(parts) > 1:
                self.tuple = [Type(part) for part in parts]
                return
            remainder = inner.strip()
        if remainder.startswith("{") and remainder.endswith("}"):
            self.atoms = [atom.strip() for atom in remainder[1:-1].split(",") if atom.strip()]
            return
        parts = [part.strip() for part in remainder.split("|") if part.strip()]
        if len(parts) > 1:   # a union may mark many on any member: Release | TasteNote[]
            subtypes = [Type(part) for part in parts]
            order = ["one", "lone", "some", "set"]
            self.multiplicity = max([self.multiplicity] + [subtype.multiplicity for subtype in subtypes], key=order.index)
            parts = [name for subtype in subtypes for name in subtype.names]
        self.names = parts

    def references(self):
        return [name for element in self.tuple for name in element.references()] if self.tuple else list(self.names)


class World:
    """Everything the module will declare, with the name each element of the model gets in it."""

    def __init__(self, model):
        self.model, document = model, model.document
        self.problems = []
        self.signatures, self.fields, self.predicates, self.atoms = {}, {}, {}, {}
        self.enumerations, self.kinds = {}, {}          # enum name -> atoms; call kind -> {field: decl}
        self.states, self.runs = {}, {}          # state level id -> info; workflow level id -> info
        self.variable_fields, self.variable_signatures = set(), set()
        self.query, self.change = {}, {}         # op slug -> info
        self.rule_name = {rule["slug"]: lower(rule["slug"]) for rule in document["rules"]}
        self._types()
        self._components()
        self._levels()
        self._operations()
        self._events()

    def _signature(self, name, **info):
        if name in self.signatures and self.signatures[name].get("kind") != info.get("kind"):
            self.problems.append(f"{name} names both a {self.signatures[name]['kind']} and a {info['kind']}; rename one")
        self.signatures.setdefault(name, info)

    def _types(self):
        for name, text in (self.model.document.get("types") or {}).items():
            literal = re.match(r"\s*(\{[^}]*\})", str(text))
            if literal:
                self._enumeration(name, Type(literal.group(1)).atoms, f"type {name}")
            else:
                self._signature(name, kind="outside")
        for primitive in sorted(PRIMITIVE_SIGNATURES):
            self._signature(primitive, kind="primitive", used=False)

    def _enumeration(self, name, atoms, where):
        if name in self.enumerations:
            if self.enumerations[name] != atoms:
                self.problems.append(f"{where}: two literal sets are both called {name}; name them in types")
            return name
        for atom in atoms:
            if not re.fullmatch(MEMBER, atom):
                self.problems.append(f"{where}: value {atom} is a lowerCamel name")
            if atom in self.atoms and self.atoms[atom] != name:
                self.problems.append(f"{where}: value {atom} is already in {self.atoms[atom]}; share one type in types")
            self.atoms[atom] = name
        self.enumerations[name] = atoms
        self._signature(name, kind="enum")
        return name

    def type_declaration(self, type_expression, where, name_hint):
        """Alloy for a type expression, registering literal sets as enums."""
        if type_expression.tuple:
            return " -> ".join(self.type_declaration(element, where, name_hint) for element in type_expression.tuple)
        if type_expression.atoms is not None:
            same = [name for name, atoms in self.enumerations.items() if atoms == type_expression.atoms]
            return same[0] if same else self._enumeration(identifier(name_hint), type_expression.atoms, where)
        union = " + ".join("Int" if name in PRIMITIVE_INTEGERS else name for name in type_expression.names)
        return f"({union})" if len(type_expression.names) > 1 else union

    def _components(self):
        document = self.model.document
        for level in document["levels"]:
            if level["kind"] != "topology":
                continue
            for node in level["nodes"]:
                parents = [identifier(self.model.nodes[edge["to"]]["label"]) for edge in level["edges"]
                           if edge["from"] == node["id"] and self.model.is_abstract(level, edge["to"])]
                self._signature(identifier(node["label"]), kind="component", node=node["id"], abstract=bool(node.get("abstract")),
                          singleton=bool(node.get("singleton")), parents=parents)
        labels = [edge.get("label", "") for level in document["levels"] if level["kind"] == "workflow" for edge in level["edges"] if not edge.get("is")]
        labels += [flow.get("edge", "") for level in document["levels"] for flow in level.get("in", []) + level.get("out", [])]
        self.artifact_words = set().union(*map(artifact_types, labels))

    def use_type(self, name, where):
        if name in PRIMITIVE_INTEGERS or name == "None":
            return
        if name == "Bool":
            self.problems.append(f"{where}: Bool is only for attributes; use a literal set such as {{yes, no}} or a subset")
            return
        if name in self.signatures:
            self.signatures[name]["used"] = True
        elif name in self.artifact_words:
            self._signature(name, kind="artifact", used=True)
        else:
            self.problems.append(f"{where}: {name} is no component, artifact, enum or declared type")

    def _attributes(self):
        for level in self.model.document["levels"]:
            for node in level["nodes"]:
                for attribute in node.get("attrs", []):
                    declaration = re.fullmatch(rf"({MEMBER})\s*:\s*(.+)", attribute)
                    if not declaration:
                        continue
                    yield level, node, declaration.group(1), Type(declaration.group(2))

    def _levels(self):
        document = self.model.document
        for level, node, name, type_expression in self._attributes():
            owner = identifier(node["label"])
            if type_expression.names == ["Bool"]:
                self._signature(identifier(name), kind="subset", of=owner)
                continue
            for reference in type_expression.references():
                self.use_type(reference, f"{node['label']}.{name}")
            declaration = self.type_declaration(type_expression, f"{node['label']}.{name}", name)
            self.fields.setdefault(name, []).append({"owner": owner, "mult": type_expression.multiplicity if not type_expression.tuple else "set", "decl": declaration, "type": type_expression})
        for level in document["levels"]:   # a relation no attribute stands for is a field named by its verb
            if level["kind"] != "topology":
                continue
            for edge in level["edges"]:
                if self.model.is_abstract(level, edge["to"]) or edge.get("attr"):
                    continue
                owner, to = identifier(self.model.nodes[edge["from"]]["label"]), identifier(self.model.nodes[edge["to"]]["label"])
                if any(field["owner"] == owner and to in (field["type"].references() if field.get("type") else []) for declared in self.fields.values() for field in declared):
                    continue
                candidates = self.fields.setdefault(lower(edge["label"]), [])
                same = next((field for field in candidates if field["owner"] == owner and field.get("relation")), None)
                if same:   # one verb from one component to several: one field over their union
                    same["decl"] += " + " + to
                    same["type"] = Type(" | ".join(type_name + "[]" for type_name in same["decl"].split(" + ")))
                else:
                    candidates.append({"owner": owner, "mult": "set", "decl": to, "type": Type(to + "[]"), "relation": edge["label"]})
        for level in document["levels"]:
            if level["kind"] == "state":
                subject = level.get("subject")
                if not subject:
                    self.problems.append(f'{level["id"]}: name the subject, the thing whose states these are')
                    continue
                self.use_type(subject, f'{level["id"]} subject')
                region = {node["id"]: node.get("partition") or "_" for node in level["nodes"]}
                for node in level["nodes"]:
                    self._signature(identifier(node["label"]), kind="state", of=subject, level=level["id"])
                    self.variable_signatures.add(identifier(node["label"]))
                self.states[level["id"]] = {"subject": subject, "region": region}
            elif level["kind"] == "workflow":
                run_signature = identifier(level["title"])
                self._signature(run_signature, kind="run", level=level["id"], used=True)
                steps = [identifier(node["label"]) for node in level["nodes"]]
                for step in steps:
                    self.atoms[step] = run_signature + "Step"
                self.enumerations[run_signature + "Step"] = steps
                self._signature(run_signature + "Step", kind="enum")
                self.runs[level["id"]] = {"run": run_signature, "steps": steps}

    def _operations(self):
        sits = self.model.sits()
        moving = {level_id for level_id in self.states} | {level_id for level_id in self.runs}
        for operation in self.model.document["operations"]:
            operation_slug = operation["slug"]
            if operation_slug not in self.model.signatures:
                continue
            receiver, verb = operation_slug.split(".")
            signature_match = re.fullmatch(r"\s*\((.*)\)\s*→\s*(.+)", operation["sig"])
            parameters = []
            for parameter in split_top(signature_match.group(1)):
                if ":" not in parameter:
                    continue
                parameter_name, parameter_type = parameter.split(":", 1)
                type_expression = Type(parameter_type)
                for reference in type_expression.references():
                    self.use_type(reference, operation_slug)
                parameters.append((parameter_name.strip(), type_expression, self.type_declaration(type_expression, operation_slug, parameter_name.strip())))
            result_type = Type(signature_match.group(2))
            for reference in result_type.references():
                self.use_type(reference, operation_slug)
            self.use_type(receiver, operation_slug)
            result_declaration = None if result_type.names == ["None"] else self.type_declaration(result_type, operation_slug, verb + "Result")
            on = sits.get(operation_slug, set())
            placed_moving = any((element_kind == "node" and self.model.node_level[element_id] in moving) or element_kind in ("edge", "trig") for element_kind, element_id in on)
            info = {"slug": operation_slug, "receiver": receiver, "verb": verb, "params": parameters, "result": result_type, "rdecl": result_declaration,
                    "pre": operation.get("pre"), "post": operation.get("post"), "modifies": operation.get("modifies", [])}
            if operation.get("modifies") or placed_moving:
                kind = receiver + verb[0].upper() + verb[1:]
                info["kind"] = kind
                fields = {"self": f"one {receiver}"}
                for parameter_name, type_expression, declaration in parameters:
                    fields[parameter_name] = f"{self._multiplicity(type_expression)} {declaration}"
                if result_declaration:
                    fields["result"] = f"{self._multiplicity(result_type)} {result_declaration}"
                self.kinds[kind] = fields
                self.change[operation_slug] = info
                self._predicate(verb, [receiver] + [declaration for _, _, declaration in parameters] + ([result_declaration] if result_declaration else []), operation_slug)
                self._predicate(verb, [receiver], operation_slug)
            else:
                self.query[operation_slug] = info
                arrow = " -> ".join([declaration for _, _, declaration in parameters] + [f"{self._multiplicity(result_type)} {result_declaration or 'univ'}"]) if parameters else f"{self._multiplicity(result_type)} {result_declaration or 'univ'}"
                self.fields.setdefault(verb, []).append({"owner": receiver, "mult": "query", "decl": arrow, "op": operation_slug})
            for modified in operation.get("modifies", []):
                modified_match = re.fullmatch(rf"({TYPE})\.({MEMBER})", modified)
                ok = modified_match and (any(field["owner"] == modified_match.group(1) and field["mult"] != "query" for field in self.fields.get(modified_match.group(2), []))
                             or self.signatures.get(identifier(modified_match.group(2)), {}).get("of") == modified_match.group(1))
                if not ok:
                    self.problems.append(f"{operation_slug}: modifies {modified}, which is no Type.attribute")
                    continue
                self.variable_fields.add((modified_match.group(1), modified_match.group(2)))
                if self.signatures.get(identifier(modified_match.group(2)), {}).get("kind") == "subset":
                    self.variable_signatures.add(identifier(modified_match.group(2)))

    @staticmethod
    def _multiplicity(type_expression):
        return "set" if type_expression.tuple else type_expression.multiplicity

    def _predicate(self, name, types, where):
        signature = tuple(types)
        have = self.predicates.setdefault(name, [])
        if any(entry["types"] == signature and entry["where"] != where for entry in have):
            self.problems.append(f"{where}: {name}{list(signature)} is declared twice; rename one")
        if not any(entry["types"] == signature for entry in have):
            have.append({"types": signature, "where": where})

    def _events(self):
        self.edge_kind = {}       # edge key -> call kind
        self.event_predicate = {}      # (level id, label) -> pred name
        model = self.model
        for level_id, info in self.states.items():
            level, subject = model.levels[level_id], info["subject"]
            for k, (edge_level, edge) in model.edges.items():
                if edge_level["id"] != level_id:
                    continue
                operation_slugs = [operation_slug for operation_slug in edge.get("ops", []) if operation_slug in self.change]
                if len(edge.get("ops", [])) > 1:
                    self.problems.append(f'{level_id}: event {edge["label"]} carries one operation, not {len(edge["ops"])}')
                if operation_slugs:
                    operation = self.change[operation_slugs[0]]
                    if operation["receiver"] != subject:
                        self.problems.append(f'{level_id}: event {edge["label"]} calls {operation_slugs[0]}, but the subject is {subject}')
                    kind, name = operation["kind"], (operation["verb"] if lower(edge["label"]) == operation["verb"] else lower(edge["label"]))
                else:
                    kind, name = subject + identifier(edge["label"]), lower(edge["label"])
                    self.kinds.setdefault(kind, {"self": f"one {subject}"})
                self.edge_kind[k] = kind
                self.event_predicate[(level_id, edge["label"])] = name
                if not operation_slugs or name != self.change[operation_slugs[0]]["verb"]:
                    self._predicate(name, [subject], f'{level_id}: {edge["label"]}')
            for trigger in level.get("triggers", []):
                operation_slugs = [operation_slug for operation_slug in trigger.get("ops", []) if operation_slug in self.change]
                if operation_slugs:
                    operation = self.change[operation_slugs[0]]
                    kind, name = operation["kind"], (operation["verb"] if lower(trigger["label"]) == operation["verb"] else lower(trigger["label"]))
                else:
                    kind, name = subject + identifier(trigger["label"]), lower(trigger["label"])
                    self.kinds.setdefault(kind, {"self": f"one {subject}"})
                self.edge_kind[("trig", level_id, trigger["label"])] = kind
                self.event_predicate[(level_id, trigger["label"])] = name
                if not operation_slugs or name != self.change[operation_slugs[0]]["verb"]:
                    self._predicate(name, [subject], f'{level_id}: {trigger["label"]}')
        for level_id, info in self.runs.items():
            level, run_signature = model.levels[level_id], info["run"]
            node_operations = {node["id"]: [operation_slug for operation_slug in node.get("ops", []) if operation_slug in self.change] for node in level["nodes"]}

            def producer(node_id, label):
                for operation_slug in node_operations.get(node_id, []):
                    if set(self.change[operation_slug]["result"].references()) & artifact_types(label):
                        return self.change[operation_slug]["kind"]
                return None

            for k, (edge_level, edge) in model.edges.items():
                if edge_level["id"] != level_id:
                    continue
                kind = producer(edge["from"], edge["label"]) or run_signature + identifier(edge["label"])
                self.kinds.setdefault(kind, {})
                self.edge_kind[k] = kind
                self.event_predicate[(level_id, edge["label"])] = lower(edge["label"])
                if lower(edge["label"]) not in self.predicates:
                    self._predicate(lower(edge["label"]), [], f'{level_id}: {edge["label"]}')
            for trigger in level.get("triggers", []):
                kind = run_signature + identifier(trigger["label"])
                self.kinds.setdefault(kind, {})
                self.edge_kind[("trig", level_id, trigger["label"])] = kind
                self.event_predicate[(level_id, trigger["label"])] = lower(trigger["label"])
                self._predicate(lower(trigger["label"]), [], f'{level_id}: {trigger["label"]}')
            for flow in level.get("in", []):
                kind = run_signature + "In" + identifier(flow["edge"])
                self.kinds.setdefault(kind, {})
                self.edge_kind[("in", level_id, flow["edge"])] = kind
            for flow in level.get("out", []):
                for source_id in [flow["from"]] if isinstance(flow.get("from"), str) else flow.get("from", []):
                    kind = producer(source_id, flow["edge"]) or run_signature + "Out" + identifier(flow["edge"])
                    self.kinds.setdefault(kind, {})
                    self.edge_kind[("out", level_id, flow["edge"], source_id)] = kind
        for rule, name in self.rule_name.items():
            self._predicate(name, [], f"rule {rule}")

    def scope(self):
        free = set(self.signatures) | set(self.atoms) | set(self.fields) | set(self.predicates) | {"at"}
        member = set(self.fields) | set(self.predicates) | {"at"}
        return free, member

    def check_formula(self, text, where, extra=()):
        """Problems with one formula: it parses, and every name is bound or a word of the module."""
        try:
            uses = formula.uses(text)
        except formula.FormulaError as e:
            return [f"{where}: {e}"]
        free, member = self.scope()
        free |= set(extra)
        out = set()
        try:
            out |= {f"variable {variable} hides the {'attribute' if variable in self.fields else 'name'} {variable}; rename the variable"
                    for variable in formula.binders(text) if variable in self.fields or variable in self.signatures or variable in self.predicates or variable in self.atoms}
        except formula.FormulaError:
            pass
        for kind, name, _, bound in uses:
            if name in bound:
                continue
            if kind == "member" and name not in member and name not in free:
                out.add(f".{name} is no attribute or operation")
            elif kind in ("free", "call") and name not in free:
                guess = [signature for signature in self.signatures if signature.lower() == name.lower() or singular(signature) == name]
                out.add(f"{name} is unbound" + (f" (did you mean {guess[0]}?)" if guess else ""))
        return [f"{where}: " + "; ".join(sorted(out))] if out else []

    def dynamic(self, text, seen=()):
        """Whether a formula speaks of something that changes: a state, a var field, a call, a step, or time."""
        try:
            uses = formula.uses(text)
            if formula.temporal(text):
                return True
        except formula.FormulaError:
            return False
        varying_fields = {field for _, field in self.variable_fields}
        calls = {predicate_name for predicate_name, declared in self.predicates.items() if any(entry["where"] not in [f"rule {slug}" for slug in self.rule_name] for entry in declared)}
        rule_by = {value: slug for slug, value in self.rule_name.items()}
        fields = {field_name for field_name, declared in self.fields.items() if any(field["mult"] != "query" for field in declared)}
        for kind, name, _, bound in uses:
            if name in bound:
                continue
            is_call = kind == "call" or (name in calls and not (kind == "member" and name in fields))
            if name in self.variable_signatures or name in varying_fields or name == "at" or is_call:
                return True
            if name in rule_by and name not in seen and self.dynamic(self.model.rules[rule_by[name]]["formula"], seen + (name,)):
                return True
        return False


def classify(world):
    """rule slug -> 'guard' (behaviour, always), 'dynamic' (checked) or 'static' (assumed or ideal)."""
    model, out = world.model, {}
    sits = model.sits()
    for rule in model.document["rules"]:
        on = sits.get(rule["slug"], set())
        guard = rule["kind"] == "must" and any((element_kind == "edge" and model.edges[element_id][0]["kind"] != "topology") or element_kind == "trig" for element_kind, element_id in on)
        out[rule["slug"]] = "guard" if guard else ("dynamic" if world.dynamic(rule["formula"]) else "static")
    return out


def translate(model):
    world = World(model)
    document, classes = model.document, classify(world)
    slug = re.sub(r"[^A-Za-z0-9]", "_", document.get("title", "model"))
    lines = [f"module {slug}", f"-- {document.get('title', '')}: generated by zoom from the Schema; edit the model, not this file.", ""]

    lines.append("-- things")
    for name, signature in world.signatures.items():
        if signature["kind"] in ("primitive", "artifact", "outside") and signature.get("used", True):
            lines.append(f"sig {name} {{}}")
    for name, atoms in world.enumerations.items():
        lines.append(f"enum {name} {{ {', '.join(atoms)} }}")
    components = [(signature_name, signature) for signature_name, signature in world.signatures.items() if signature["kind"] == "component"]
    order = sorted(components, key=lambda item: (len(item[1]["parents"]) > 0, item[0]))
    # a query is a relation of one arity more than its parameters, and Kodkod refuses one over a few hundred atoms
    # beyond arity 3 ("translation capacity exceeded"): declare a query only where a formula of the module names it
    said = [rule["formula"] for rule in document["rules"]] + [level["init"] for level in model.levels.values() if level.get("init")]
    said += [condition for operation in world.change.values() for condition in (operation.get("pre"), operation.get("post")) if condition]
    named = set()
    for text in said:
        try:
            named |= {name for _, name, _, _ in formula.uses(text)}
        except formula.FormulaError:
            pass
    for name, signature in order:
        fields = []
        for field_name, declarations in world.fields.items():
            for declaration in declarations:
                if declaration["owner"] != name or (declaration["mult"] == "query" and field_name not in named):
                    continue
                variable_prefix = "var " if (name, field_name) in world.variable_fields else ""
                multiplicity = "" if declaration["mult"] == "query" else ("set " if declaration["mult"] == "set" and "->" in declaration["decl"] else declaration["mult"] + " ")
                fields.append(f"{variable_prefix}{field_name}: {multiplicity}{declaration['decl']}")
        head = ("abstract " if signature["abstract"] else "") + ("one " if signature["singleton"] else "") + f"sig {name}"
        parents = signature["parents"]
        if len(parents) == 1:
            head += f" extends {parents[0]}"
        elif len(parents) > 1:
            head += " in " + " + ".join(parents)
        lines.append(head + (" {\n  " + ",\n  ".join(fields) + "\n}" if fields else " {}"))
    for name, signature in world.signatures.items():
        if signature["kind"] == "subset":
            lines.append(f"{'var ' if name in world.variable_signatures else ''}sig {name} in {signature['of']} {{}}")
    for level_id, info in world.states.items():
        regions = {}
        for node in model.levels[level_id]["nodes"]:
            regions.setdefault(info["region"][node["id"]], []).append(identifier(node["label"]))
        for region, state_names in regions.items():
            lines.append(f"var sig {', '.join(state_names)} in {info['subject']} {{}}")
    for level_id, info in world.runs.items():
        lines.append(f"one sig {info['run']} {{ var at: set {info['run']}Step }}")

    lines += ["", "-- calls: each step of a run is the set of calls made in it", "abstract sig Call {}", "one sig Now { var happens: set Call }"]
    for kind, fields in world.kinds.items():   # a call with no arguments is one atom; others get one per argument list
        body = ", ".join(f"{k}: {value}" for k, value in fields.items())
        lines.append(f"{'' if body else 'one '}sig {kind} extends Call {{{' ' + body + ' ' if body else ''}}}")
    lines.append("pred stutter { no Now.happens }")

    lines += ["", "-- what happened in this step"]
    for operation_slug, operation in world.change.items():
        arguments = [("s", operation["receiver"])] + [(parameter_name + "_", f"{world._multiplicity(type_expression)} {parameter_declaration}") for parameter_name, type_expression, parameter_declaration in operation["params"]] + ([("result_", f"{world._multiplicity(operation['result'])} {operation['rdecl']}")] if operation["rdecl"] else [])
        matches = " and ".join(["c.self = s"] + [f"c.{parameter_name} = {parameter_name}_" for parameter_name, _, _ in operation["params"]] + (["c.result = result_"] if operation["rdecl"] else []))
        parameter_list = ", ".join(f"{alloy_name}: {alloy_type}" for alloy_name, alloy_type in arguments)
        lines.append(f"pred {operation['verb']}[{parameter_list}] {{ some c: Now.happens & {operation['kind']} | {matches} }}")
        lines.append(f"pred {operation['verb']}[s: {operation['receiver']}] {{ some c: Now.happens & {operation['kind']} | c.self = s }}")
    done = {(operation["verb"], operation["receiver"]) for operation in world.change.values()}
    for level_id, info in world.states.items():
        subject, labels = info["subject"], {}
        for k, (edge_level, edge) in model.edges.items():
            if edge_level["id"] == level_id:
                labels.setdefault(edge["label"], []).append((k, edge))
        for label, label_edges in labels.items():
            name = world.event_predicate[(level_id, label)]
            if (name, subject) in done:
                continue
            done.add((name, subject))
            kind = world.edge_kind[label_edges[0][0]]
            froms = " + ".join(sorted({identifier(model.nodes[edge["from"]]["label"]) for _, edge in label_edges}))
            lines.append(f"pred {name}[s: {subject}] {{ some c: Now.happens & {kind} | c.self = s and s in {froms} }}")
        for trigger in model.levels[level_id].get("triggers", []):
            name = world.event_predicate[(level_id, trigger["label"])]
            if (name, subject) not in done:
                done.add((name, subject))
                lines.append(f"pred {name}[s: {subject}] {{ some c: Now.happens & {world.edge_kind[('trig', level_id, trigger['label'])]} | c.self = s }}")
    for level_id, info in world.runs.items():
        for trigger in model.levels[level_id].get("triggers", []):
            lines.append(f"pred {lower(trigger['label'])} {{ some Now.happens & {world.edge_kind[('trig', level_id, trigger['label'])]} }}")
        handed = {}
        for k, (edge_level, edge) in model.edges.items():   # an artifact is handed on when its producer runs in the active step
            if edge_level["id"] == level_id:
                handed.setdefault(lower(edge["label"]), []).append(f"(some Now.happens & {world.edge_kind[k]} and {identifier(model.nodes[edge['from']]['label'])} in {info['run']}.at)")
        for name, ways in handed.items():
            lines.append(f"pred {name} {{ {' or '.join(ways)} }}")

    lines += ["", "-- rules"]
    for rule in document["rules"]:
        lines.append(f"-- {rule['slug']} ({rule['kind']}, {classes[rule['slug']]})")
        lines.append(f"pred {world.rule_name[rule['slug']]} {{\n  " + formula.layout(rule["formula"]).replace("\n", "\n  ") + "\n}")

    def superstate(level_id):
        """The state a state level is opened from, whose instances its states partition, or None."""
        parent = model.levels[level_id].get("parent")
        # a level of another subject only zooms in, since its instances are not the superstate's
        same = parent and model.node_level[parent] in world.states and world.states[model.node_level[parent]]["subject"] == world.states[level_id]["subject"]
        return identifier(model.nodes[parent]["label"]) if same else None

    def entered_by(level_id, *modes):
        """Each edge into a state level's superstate whose `enters` is one of modes, as a condition on s."""
        parent = model.levels[level_id]["parent"]
        return [f"(s in {identifier(model.nodes[edge['from']]['label'])} and some c: Now.happens & {world.edge_kind[k]} | c.self = s)"
                for k, (edge_level, edge) in model.edges.items() if edge["to"] == parent and edge["from"] != parent and edge.get("enters") in modes]

    def unless(terms):
        return f"not ({' or '.join(terms)})" if terms else ""

    def resumed(level_id):
        """When entering its superstate resumes a level, as a conjunct to add: always ("") by its own history, else
        by an edge that enters by history, or when a deep history above it is entered in the same step; None when never."""
        level = model.levels[level_id]
        terms = ([unless(entered_by(level_id, "initial"))] if level.get("history") else []) + entered_by(level_id, "shallow", "deep")
        ancestor = model.node_level[level["parent"]]
        while superstate(ancestor):
            # an edge's own `enters` wins over the level's history for that entry
            deep = ([unless(entered_by(ancestor, "initial", "shallow"))] if model.levels[ancestor].get("history") == "deep" else []) + entered_by(ancestor, "deep")
            if deep:
                up = superstate(ancestor)
                terms.append(f"(s not in {up} and s in {up}'" + ("" if "" in deep else f" and ({' or '.join(deep)})") + ")")
            ancestor = model.node_level[model.levels[ancestor]["parent"]]
        if "" in terms:
            return ""
        return f" and ({' or '.join(terms)})" if terms else None

    behaviour_lines = []
    for level_id, info in world.states.items():
        level, subject = model.levels[level_id], info["subject"]
        regions = {}
        for node in level["nodes"]:
            regions.setdefault(info["region"][node["id"]], []).append(node)
        initial_ids = [level["initial"]] if isinstance(level.get("initial"), str) else level.get("initial") or []
        up = superstate(level_id)
        again = resumed(level_id) if up else None
        behaviour_lines.append(f"-- {level['title']}" + (f", inside {up}" if up else ""))
        behaviour_lines.append(f"all s: {up or subject} | " + " and ".join(f"s in {identifier(model.nodes[initial_id]['label'])}" for initial_id in initial_ids))
        for region, nodes in regions.items():
            state_names = [identifier(node["label"]) for node in nodes]
            behaviour_lines.append(f"always ({up or subject} = {' + '.join(state_names)}" + "".join(f" and no {first} & {second}" for position, first in enumerate(state_names) for second in state_names[position + 1:]) + ")")
            if up:   # entering the superstate enters each region at its initial state, or where history left it
                initial_state = next(identifier(model.nodes[initial_id]["label"]) for initial_id in initial_ids if info["region"][initial_id] == region)
                enter = f"s not in {up} and s in {up}'"
                held = f" and not (once (s in {' + '.join(state_names)}){again})" if again is not None else ""
                behaviour_lines.append(f"always (all s: {subject} | ({enter}{held}) implies s in {initial_state}')")
                if again is not None:
                    behaviour_lines += [f"always (all s: {subject} | ({enter}{again} and ((s not in {up}) since (s in {state_name}))) implies s in {state_name}')" for state_name in state_names]
            pairs = {}
            for k, (edge_level, edge) in model.edges.items():
                if edge_level["id"] == level_id and edge["from"] in {node["id"] for node in nodes}:
                    pairs.setdefault((world.edge_kind[k], identifier(model.nodes[edge["from"]]["label"])), set()).add(identifier(model.nodes[edge["to"]]["label"]))
            for (kind, source), targets in pairs.items():   # leaving the superstate in the same step cuts the event short
                behaviour_lines.append(f"always (all c: Now.happens & {kind} | c.self in {source}{f' and after c.self in {up}' if up else ''} implies after c.self in {' + '.join(sorted(targets))})")
            enable = {}
            for (kind, source) in pairs:
                enable.setdefault(kind, []).append(source)
            for kind, sources in enable.items():   # an event happens only in a state that handles it
                behaviour_lines.append(f"always (all c: Now.happens & {kind} | c.self in {' + '.join(sorted(sources))})")
            trigger_moves = [(world.edge_kind[("trig", level_id, trigger["label"])], identifier(model.nodes[trigger["to"]]["label"])) for trigger in level.get("triggers", []) if info["region"][trigger["to"]] == region]
            for kind, to in trigger_moves:
                behaviour_lines.append(f"always (all c: Now.happens & {kind} | after c.self in {to})")
            moves = [f"(s in {source} and some c: Now.happens & {kind} | c.self = s)" for (kind, source) in pairs] + [f"(some c: Now.happens & {kind} | c.self = s)" for kind, _ in trigger_moves]
            moves += [f"(s not in {up} and s in {up}')", f"(s in {up} and s not in {up}')"] if up else []
            same = " and ".join(f"(s in {state_name} iff s in {state_name}')" for state_name in state_names)
            behaviour_lines.append(f"always (all s: {subject} | ({same})" + "".join(f"\n    or {move}" for move in moves) + ")")
        completes = sorted({world.edge_kind[k] for k, (edge_level, edge) in model.edges.items() if up and edge["from"] == level["parent"] and edge.get("completion")})
        if completes:   # the completion event fires as soon as every region holds a final state, and never before
            finals = [" + ".join(identifier(node["label"]) for node in nodes if node.get("final")) for nodes in regions.values()]
            if all(finals):
                every = " and ".join(f"s in ({final})" for final in finals)
                # one clause per call kind, since each declares its own self and Alloy types no join over their union
                behaviour_lines += [f"always (all c: Now.happens & {call_kind} | let s = c.self | {every})" for call_kind in completes]
                behaviour_lines.append(f"always (all s: {up} | {every} implies " + " or ".join(f"(some c: Now.happens & {call_kind} | c.self = s)" for call_kind in completes) + ")")
        for sync in level.get("syncs", []):
            when, then = world.event_predicate[(level_id, sync["when"])], world.event_predicate[(level_id, sync["then"])]
            where = f" and s in {identifier(model.nodes[sync['where']]['label'])}" if sync.get("where") else ""
            behaviour_lines.append(f"always (all s: {subject} | (s.{when}{where}) implies s.{then})   -- sync {sync['name']}")
    for level_id, info in world.runs.items():
        level, run_signature = model.levels[level_id], info["run"]
        behaviour_lines.append(f"-- {level['title']}")
        opened = level.get("triggers") or level.get("in")   # a run opened from outside starts empty; otherwise at its first steps
        firsts = [identifier(node["label"]) for node in level["nodes"] if not any(edge["to"] == node["id"] and edge["from"] != node["id"] for edge in level["edges"])]
        behaviour_lines.append(f"no {run_signature}.at" if opened or not firsts else f"{run_signature}.at = {' + '.join(firsts)}")
        entering, leaving = {}, {}
        pairs = {}
        for k, (edge_level, edge) in model.edges.items():
            if edge_level["id"] != level_id:
                continue
            source, to = identifier(model.nodes[edge["from"]]["label"]), identifier(model.nodes[edge["to"]]["label"])
            pairs.setdefault((world.edge_kind[k], source), set()).add(to)
        for outgoing in level.get("out", []):
            for source_id in [outgoing["from"]] if isinstance(outgoing.get("from"), str) else outgoing.get("from", []):
                pairs.setdefault((world.edge_kind[("out", level_id, outgoing["edge"], source_id)], identifier(model.nodes[source_id]["label"])), set())
        starts = [(world.edge_kind[("trig", level_id, trigger["label"])], identifier(model.nodes[trigger["to"]]["label"])) for trigger in level.get("triggers", [])]
        starts += [(world.edge_kind[("in", level_id, incoming["edge"])], identifier(model.nodes[incoming["to"]]["label"])) for incoming in level.get("in", [])]
        for (kind, source), targets in pairs.items():
            stay = source in targets
            effect = (f"some ({' + '.join(sorted(targets))}) & {run_signature}.at'" if targets else "") + ("" if stay else (" and " if targets else "") + f"{source} not in {run_signature}.at'")
            behaviour_lines.append(f"always ((some Now.happens & {kind} and {source} in {run_signature}.at) implies {effect})")
            for target in targets:
                entering.setdefault(target, []).append(f"(some Now.happens & {kind} and {source} in {run_signature}.at)")
            leaving.setdefault(source, []).append(f"(some Now.happens & {kind} and {source} in {run_signature}.at)")
        for kind, to in starts:
            behaviour_lines.append(f"always (some Now.happens & {kind} implies {to} in {run_signature}.at')")
            entering.setdefault(to, []).append(f"some Now.happens & {kind}")
        for step in info["steps"]:
            entered = " or ".join(entering.get(step, [])) or "some none"
            left = " or ".join(leaving.get(step, [])) or "some none"
            behaviour_lines.append(f"always ({step} not in {run_signature}.at and {step} in {run_signature}.at' implies ({entered}))")
            behaviour_lines.append(f"always ({step} in {run_signature}.at and {step} not in {run_signature}.at' implies ({left}))")
    behaviour_lines.append("-- operations")
    for level_id, info in world.states.items():   # an operation drawn on a state runs only while its subject is there
        for node in model.levels[level_id]["nodes"]:
            for drawn_slug in node.get("ops", []):
                operation = world.change.get(drawn_slug)
                if not operation:
                    continue
                argument = "self" if operation["receiver"] == info["subject"] else next((parameter_name for parameter_name, type_expression, _ in operation["params"] if type_expression.names == [info["subject"]]), None)
                if argument:
                    behaviour_lines.append(f"always (all c: Now.happens & {operation['kind']} | c.{argument} in {identifier(node['label'])})")
    for operation_slug, operation in world.change.items():
        renames = {"self": "c.self", "result": "c.result"} | {parameter_name: "c." + parameter_name for parameter_name, _, _ in operation["params"]}
        conditions = [formula.rename(condition, renames) for condition in (operation.get("pre"), operation.get("post")) if condition]
        if conditions:
            behaviour_lines.append(f"always (all c: Now.happens & {operation['kind']} | " + " and ".join(f"({condition})" for condition in conditions) + ")")
    for owner, field in sorted(world.variable_fields):
        kinds = sorted({operation["kind"] for operation in world.change.values() if f"{owner}.{field}" in operation["modifies"]})
        if not kinds:
            continue
        modifiers = [operation for operation in world.change.values() if f"{owner}.{field}" in operation["modifies"]]
        by = " or ".join(f"(some c: Now.happens & {operation['kind']} | c.self = x)" if operation["receiver"] == owner else f"some Now.happens & {operation['kind']}"
                         for operation in sorted(modifiers, key=lambda candidate: candidate["kind"]))
        subset_name = identifier(field)
        if world.signatures.get(subset_name, {}).get("kind") == "subset" and world.signatures[subset_name]["of"] == owner:
            behaviour_lines.append(f"always (all x: {owner} | (x in {subset_name} iff x in {subset_name}') or {by})")
        else:
            behaviour_lines.append(f"always (all x: {owner} | x.{field}' = x.{field} or {by})")
    for rule in document["rules"]:
        if classes[rule["slug"]] == "guard":
            behaviour_lines.append(f"always {world.rule_name[rule['slug']]}   -- guard")
    for level_id in model.levels:
        if model.levels[level_id].get("init"):
            behaviour_lines.append(f"{model.levels[level_id]['init']}   -- init of {level_id}")
    lines += ["", "-- how things move", "pred behaviour {\n  " + "\n  ".join(behaviour_lines) + "\n}"]

    musts_static = [world.rule_name[rule["slug"]] for rule in document["rules"] if classes[rule["slug"]] == "static" and rule["kind"] == "must"]

    checks = []
    for rule in document["rules"]:   # every rule is asked, a static one under the others, so none is assumed to prove itself
        me = world.rule_name[rule["slug"]]
        given = " and ".join([static_name for static_name in musts_static if static_name != me] + ["behaviour"])
        checks.append((f"holds_{me}", "check", f"{given} implies always {me}", 0 if rule["kind"] == "must" else None, rule["slug"]))
    lines += ["", "-- what Alloy checks"]
    scopes = {rule["slug"]: rule["scope"] for rule in document["rules"] if rule.get("scope")}
    for name, _, body, expected, slug in checks:
        calls = len(world.kinds) + 3   # room for every kind of call at least once, and a few repeats
        more = f", {scopes[slug]}" if slug in scopes else ""
        lines.append(f"check {name} {{ {body} }} for 3 but {calls} Call, 8 steps{more}" + (f" expect {expected}" if expected is not None else ""))
    return "\n".join(lines) + "\n", world, checks


def _pinned(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() == JAR_SHA256


_checked = {}   # (path, size, mtime) -> whether it matched the pin, so a jar is hashed once per change


def jar():
    """The jar to run: the one ALLOY_JAR names, since the owner chose that file, or the cached one when it matches
    the pin. A cached file that does not match is refused (None), as a download would be."""
    named_jar = os.environ.get("ALLOY_JAR")
    if named_jar and Path(named_jar).is_file():
        return named_jar
    cached = Path.home() / ".cache/paperwork-alloy/alloy.jar"
    if not cached.is_file():
        return None
    status = cached.stat()
    key = (str(cached), status.st_size, status.st_mtime_ns)
    if key not in _checked:
        _checked[key] = _pinned(cached)
        if not _checked[key]:
            print(f"{cached} is not the pinned {JAR_URL} (sha256 {JAR_SHA256}); refused", file=sys.stderr)
    return str(cached) if _checked[key] else None


def ready():
    """Whether Alloy can run here: a jar and a `java` to run it."""
    return bool(jar() and shutil.which("java"))


def fetch():
    destination = Path.home() / ".cache/paperwork-alloy/alloy.jar"
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-sSL", "-o", str(destination), JAR_URL], check=True)
    if not _pinned(destination):
        destination.unlink()
        raise SystemExit(f"alloy.jar is not the pinned {JAR_URL}; deleted")
    return str(destination)


CACHE = Path.home() / ".cache/paperwork-alloy/results"
SECONDS = int(os.environ.get("PAPERWORK_ALLOY_SECONDS", "120"))
JAVA_PROCESSES = min(os.cpu_count() or 1, 4)


def _split(text):
    """The module above the commands, the commands, and the key and name of a command."""
    import hashlib
    i = text.index("-- what Alloy checks")
    head, commands = text[:i], [command for command in text[i:].splitlines()[1:] if command.strip()]
    key = lambda command: hashlib.sha256((head + "\n" + command).encode()).hexdigest()
    name_of = lambda command: re.match(r"\s*(?:run|check)\s+(\w+)", command).group(1)
    return head, commands, key, name_of


def _stored(text):
    """The stored answer of every command whose text (with the module above it) was answered before; one that ran
    out of time stays unanswered unless given more time now."""
    head, commands, key, name_of = _split(text)
    stored = {command: json.loads((CACHE / key(command)).read_text()) for command in commands if (CACHE / key(command)).exists()}
    return {command: answer for command, answer in stored.items() if answer.get("slow", SECONDS) >= SECONDS}


def _result(text, stored):
    import hashlib
    head, commands, key, name_of = _split(text)
    warn_file = CACHE / (hashlib.sha256(head.encode()).hexdigest() + ".warnings")
    warn = json.loads(warn_file.read_text()) if warn_file.exists() else []
    results = {name_of(command): answer for command, answer in stored.items() if "slow" not in answer}
    return results, warn, [name_of(command) for command, answer in stored.items() if "slow" in answer]


def cached(text):
    """Alloy's stored answers for a module, without starting Alloy: {name: {sat, instances}, _warnings, _ran, _slow}."""
    if not CACHE.is_dir():
        return {"_warnings": [], "_ran": 0, "_slow": []}
    results, warn, slow = _result(text, _stored(text))
    results["_warnings"], results["_ran"], results["_slow"] = warn, 0, slow
    return results


def run(text):
    """Run each command whose text (with the module above it) is new, one process per command, at most JAVA_PROCESSES at
    once, with Glucose and at most SECONDS each; reuse the stored answer of every other. A command that runs out
    of time is left unanswered and listed in _slow. Returns {name: {sat, instances}, _warnings, _ran, _slow}, or
    None where Alloy cannot run."""
    import hashlib
    from concurrent.futures import ThreadPoolExecutor
    if not ready():
        return None
    jar_path = jar()
    head, commands, key, name_of = _split(text)
    CACHE.mkdir(parents=True, exist_ok=True)
    stored = _stored(text)
    todo = [command for command in commands if command not in stored]
    warn_file = CACHE / (hashlib.sha256(head.encode()).hexdigest() + ".warnings")
    results, warn, slow = _result(text, stored)
    work = tempfile.mkdtemp(prefix="paperwork-alloy-")   # private to this run: two checks at once never share a file

    def one(index, command):
        part, out = Path(work) / f"c{index}.als", Path(work) / f"o{index}"
        part.write_text(head + "-- what Alloy checks\n" + command + "\n")
        try:
            completed = subprocess.run(["java", "-jar", jar_path, "exec", "-f", "-s", "glucose", "-o", str(out), str(part)],
                                       capture_output=True, text=True, timeout=SECONDS)
        except subprocess.TimeoutExpired:
            return command, None, None, ""
        return command, completed.stdout + completed.stderr, out / "receipt.json", part.read_text()

    try:
        with ThreadPoolExecutor(JAVA_PROCESSES) as pool:
            for command, log, receipt, module in pool.map(lambda index_command: one(*index_command), enumerate(todo)):
                if log is None:
                    slow.append(name_of(command))
                    (CACHE / key(command)).write_text(json.dumps({"slow": SECONDS}))
                    continue
                if not receipt.exists():
                    error_lines = [line for line in log.splitlines() if ("error" in line.lower() or "line" in line or "capacity" in line or "cannot be" in line) and "JAVA_TOOL" not in line and not line.strip().startswith("at ")]
                    raise RuntimeError("\n".join(error_lines[:6]) or "no receipt from Alloy")
                if command == todo[0]:   # type warnings belong to the module, so one command's log has them all
                    warn = warnings(log, module)
                for name, outcome in json.loads(receipt.read_text())["commands"].items():
                    solutions = outcome.get("solution") or []
                    sat = bool(solutions and solutions[0].get("instances"))
                    results[name] = {"sat": sat, "instances": solutions[0].get("instances") if sat else None}
                    (CACHE / key(command)).write_text(json.dumps(results[name]))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if todo:
        warn_file.write_text(json.dumps(warn))
    results["_warnings"], results["_ran"], results["_slow"] = warn, len([command for command in todo if name_of(command) not in slow]), slow
    return results


def warnings(text, module):
    """Alloy's type warnings, each as the line of the module it points at and Alloy's reason."""
    source_lines = module.splitlines()
    out = []
    for found in re.finditer(r"line (\d+), column \d+.*?\n(.+?)(?:\n(?:Left|Right) type|\n\s*\d+\. |\Z)", text, re.S):
        line = source_lines[int(found.group(1)) - 1].strip() if int(found.group(1)) <= len(source_lines) else ""
        reason = " ".join(found.group(2).split())
        if "unused" in reason:
            continue
        out.append(f"{reason} — in: {line[:120]}")
    return out


def calls_in(instances, world=None):
    """The calls made at each step of a run, named as the model names them (an operation, event or trigger)."""
    names = {}
    if world:
        for operation in world.change.values():
            names[operation["kind"]] = operation["slug"]
        for k, kind in world.edge_kind.items():
            if kind not in names:
                names[kind] = world.model.edges[k][1]["label"] if k in world.model.edges else k[2] if isinstance(k, tuple) else kind
    steps = []
    for instance in instances or []:
        now = next((value for k, value in instance["values"].items() if k.startswith("Now$")), {})
        steps.append(sorted({names.get(re.sub(r"\$\d+$", "", call[0]), re.sub(r"\$\d+$", "", call[0])) for call in now.get("happens", [])}))
    return steps


def sit_ids(model, slug):
    """The ids of the nodes and edges an operation or rule sits on, a trigger standing for the node it enters."""
    return {model.triggers[element_id][1]["to"] if element_kind == "trig" else element_id for element_kind, element_id in model.sits().get(slug, ())}


def element_ids(world):
    """Each call kind and each signature, as the ids of the Schema nodes and edges they stand for."""
    model, kinds = world.model, {}
    for k, kind in world.edge_kind.items():
        if isinstance(k, str):
            ids = {k}
        else:
            level = model.levels[k[1]]
            ids = ({trigger["to"] for trigger in level.get("triggers", []) if trigger["label"] == k[2]} if k[0] == "trig"
                   else {flow["to"] for flow in level.get("in", []) if flow["edge"] == k[2]} if k[0] == "in" else {k[3]})
        kinds.setdefault(kind, set()).update(ids)
    for operation in world.change.values():   # a call drawn as an edge is that edge; another is where its operation sits
        if operation["kind"] not in kinds:
            kinds[operation["kind"]] = sit_ids(model, operation["slug"])
    signatures = {}
    for node in model.nodes.values():
        signatures.setdefault(identifier(node["label"]), node["id"])
    return kinds, signatures


def trace(world, instances, slug):
    """A counterexample as Schema ids: the nodes whose things witness it, in brackets, then the elements called at
    each step, ` + ` within a step and `|` between elements one call may stand for; where it names neither, the
    nodes and edges the rule sits on."""
    kinds, signatures = element_ids(world)
    atom = lambda atom_id: re.sub(r"\$\d+$", "", atom_id)

    def node_of(signature, seen=()):
        if signature in signatures:
            return signatures[signature]
        for parent in world.signatures.get(signature, {}).get("parents", []):
            if parent not in seen and (node_id := node_of(parent, seen + (signature,))):
                return node_id
        return None

    witness = sorted({node_id for skolem in (instances[0].get("skolems") or {}).values() for row in skolem.get("data", [])
                      for cell in row if (node_id := node_of(atom(cell)))}) if instances else []
    steps = []
    for instance in instances or []:
        now = next((value for k, value in instance["values"].items() if k.startswith("Now$")), {})
        step = sorted({"|".join(sorted(kinds.get(atom(call[0]), ()))) for call in now.get("happens", [])} - {""})
        if step:
            steps.append(" + ".join(step))
    parts = ([f"[{', '.join(witness)}]"] if witness else []) + ([" → ".join(steps)] if steps else [])
    return " ".join(parts) or ", ".join(sorted(sit_ids(world.model, slug)))


def story(steps):
    """A run as one line: the calls of each step, in order; empty steps are dropped."""
    return " → ".join(" + ".join(step) for step in steps if step) or "no call at all"


def stored(model):
    """The module's names, its commands and the answers stored for them: Alloy is never started."""
    alloy_text, world, checks = translate(model)
    return world, checks, cached(alloy_text)


def standing(model, world, results):
    """Each rule's standing for the page: guard, assumed, ideal, holds or not checked, and the run that breaks it."""
    classes, out = classify(world), {}
    for rule in model.document["rules"]:
        rule_class = classes[rule["slug"]]
        answer = (results or {}).get(f"holds_{world.rule_name[rule['slug']]}")
        role = {"guard": "guard", "static": "assumed" if rule["kind"] == "must" else "ideal"}.get(rule_class) or ("holds" if answer else "not checked")
        out[rule["slug"]] = (role, [step for step in calls_in(answer["instances"], world) if step] if answer and answer["sat"] else None)
    return out


def verdicts(model, world, checks, results):
    """Notes (Alloy's type warnings, a should rule that can break) and findings (a must rule the behaviour can
    break: a defect of the system, reported, never fixed by bending the model)."""
    notes, findings = [f"Alloy warns: {warning}" for warning in results.get("_warnings", [])], []
    for name, _, _, expected, what in checks:
        answer = results.get(name)
        if answer and answer["sat"]:
            (findings if expected == 0 else notes).append(f"{what}: can break in this run: {story(calls_in(answer['instances'], world))}")
    return notes, findings

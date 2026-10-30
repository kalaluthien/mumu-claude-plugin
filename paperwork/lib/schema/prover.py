"""The model in Alloy 6: the names it declares, its translation to a module, and running that module.

Translation is deterministic. Parts and outside types become signatures; attributes and calls become fields; states
become mutable subsets of the level's subject. Every transition is reified as a Call atom, so "x.verb happened" is a
predicate on the calls of the current step (Practical Alloy's event idiom). Formulas are already Alloy and are copied
as written.
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
from .model import MEMBER, split_top

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
        self.states = {}                                # level id -> info
        self.variable_fields, self.variable_signatures = set(), set()
        self.rule_name = {rule["slug"]: lower(rule["slug"]) for rule in document["rules"]}
        self._types()
        self._parts()
        self._levels()
        self._events()
        self._changes()

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

    def _parts(self):
        for level_id, level in self.model.levels.items():
            for node in level["nodes"]:
                if node["id"] not in self.model.states(level_id):
                    self._signature(identifier(node["label"]), kind="component", node=node["id"])

    def use_type(self, name, where):
        if name in PRIMITIVE_INTEGERS or name == "None":
            return
        if name == "Bool":
            self.problems.append(f"{where}: Bool is only for attributes; use a literal set such as {{yes, no}} or a subset")
            return
        if name in self.signatures:
            self.signatures[name]["used"] = True
        else:
            self.problems.append(f"{where}: {name} is no part, enum or declared type")

    def _attributes(self):
        for level in self.model.levels.values():
            for node in level["nodes"]:
                for attribute in node.get("attrs", []):
                    declaration = re.fullmatch(rf"({MEMBER})\s*:\s*(.+)", attribute)
                    if not declaration:
                        continue
                    yield level, node, declaration.group(1), Type(declaration.group(2))

    def _levels(self):
        model = self.model
        for level, node, name, type_expression in self._attributes():
            owner = identifier(node["label"])
            if type_expression.names == ["Bool"]:
                self._signature(identifier(name), kind="subset", of=owner)
                continue
            for reference in type_expression.references():
                self.use_type(reference, f"{node['label']}.{name}")
            declaration = self.type_declaration(type_expression, f"{node['label']}.{name}", name)
            self.fields.setdefault(name, []).append({"owner": owner, "mult": type_expression.multiplicity if not type_expression.tuple else "set", "decl": declaration, "type": type_expression})
        for level_id, level in model.levels.items():   # a call no attribute stands for is a field named by its verb
            states = model.states(level_id)
            for edge in level["edges"]:
                if edge["kind"] != "call" or edge.get("attr") or {edge["from"], edge["to"]} & states:
                    continue
                owner, to = identifier(model.nodes[edge["from"]]["label"]), identifier(model.nodes[edge["to"]]["label"])
                if any(field["owner"] == owner and to in field["type"].references() for declared in self.fields.values() for field in declared):
                    continue
                candidates = self.fields.setdefault(lower(edge["label"]), [])
                same = next((field for field in candidates if field["owner"] == owner and field.get("relation")), None)
                if same:   # one verb from one part to several: one field over their union
                    same["decl"] += " + " + to
                    same["type"] = Type(" | ".join(type_name + "[]" for type_name in same["decl"].split(" + ")))
                else:
                    candidates.append({"owner": owner, "mult": "set", "decl": to, "type": Type(to + "[]"), "relation": edge["label"]})
        for level_id, level in model.levels.items():
            states = model.states(level_id)
            if not states:
                continue
            subject = level.get("subject")
            if not subject:
                self.problems.append(f"{level_id}: name the subject, the thing whose states these are")
                continue
            self.use_type(subject, f"{level_id} subject")
            for node in level["nodes"]:
                if node["id"] in states:
                    self._signature(identifier(node["label"]), kind="state", of=subject, level=level_id)
                    self.variable_signatures.add(identifier(node["label"]))
            self.states[level_id] = {"subject": subject, "region": {node["id"]: node.get("region") or "_" for node in level["nodes"] if node["id"] in states}}

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
        for level_id, info in self.states.items():
            subject = info["subject"]
            for key, (edge_level, edge) in self.model.edges.items():
                if edge_level == level_id and edge["kind"] == "transition":
                    kind, name = subject + identifier(edge["label"]), lower(edge["label"])
                    self.kinds.setdefault(kind, {"self": f"one {subject}"})
                    self.edge_kind[key] = kind
                    self.event_predicate[(level_id, edge["label"])] = name
                    self._predicate(name, [subject], f'{level_id}: {edge["label"]}')
        for rule, name in self.rule_name.items():
            self._predicate(name, [], f"rule {rule}")

    def _changes(self):
        """Who may change what: (owner, attribute) -> the kinds of call that may."""
        self.changed = {}
        for key, (level_id, edge) in self.model.edges.items():
            for changed in edge.get("changes", []):
                owner, attribute = changed.split(".")
                subset = self.signatures.get(identifier(attribute), {})
                if not (any(field["owner"] == owner for field in self.fields.get(attribute, [])) or subset.get("of") == owner):
                    self.problems.append(f'{level_id}: {edge["label"]} changes {changed}, which is no attribute')
                elif key in self.edge_kind:
                    self.variable_fields.add((owner, attribute))
                    self.variable_signatures |= {identifier(attribute)} if subset.get("kind") == "subset" else set()
                    self.changed.setdefault((owner, attribute), set()).add((self.edge_kind[key], self.states[level_id]["subject"]))

    def scope(self):
        free = set(self.signatures) | set(self.atoms) | set(self.fields) | set(self.predicates)
        member = set(self.fields) | set(self.predicates)
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
        fields = set(self.fields)
        for kind, name, _, bound in uses:
            if name in bound:
                continue
            is_call = kind == "call" or (name in calls and not (kind == "member" and name in fields))
            if name in self.variable_signatures or name in varying_fields or is_call:
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
        guard = rule["kind"] == "must" and any(element_kind == "edge" and model.edges[element_id][1]["kind"] == "transition" for element_kind, element_id in on)
        out[rule["slug"]] = "guard" if guard else ("dynamic" if world.dynamic(rule["formula"]) else "static")
    return out


def translate(model):
    world = World(model)
    document, classes = model.document, classify(world)
    slug = re.sub(r"[^A-Za-z0-9]", "_", document["title"])
    lines = [f"module {slug}", f"-- {document['title']}: generated by zoom from the Schema; edit the document, not this file.", ""]

    lines.append("-- things")
    for name, signature in world.signatures.items():
        if signature["kind"] in ("primitive", "outside") and signature.get("used", True):
            lines.append(f"sig {name} {{}}")
    for name, atoms in world.enumerations.items():
        lines.append(f"enum {name} {{ {', '.join(atoms)} }}")
    for name in sorted(name for name, signature in world.signatures.items() if signature["kind"] == "component"):
        fields = []
        for field_name, declarations in world.fields.items():
            for declaration in declarations:
                if declaration["owner"] == name:
                    variable_prefix = "var " if (name, field_name) in world.variable_fields else ""
                    multiplicity = "set " if declaration["mult"] == "set" and "->" in declaration["decl"] else declaration["mult"] + " "
                    fields.append(f"{variable_prefix}{field_name}: {multiplicity}{declaration['decl']}")
        lines.append(f"sig {name}" + (" {\n  " + ",\n  ".join(fields) + "\n}" if fields else " {}"))
    for name, signature in world.signatures.items():
        if signature["kind"] == "subset":
            lines.append(f"{'var ' if name in world.variable_signatures else ''}sig {name} in {signature['of']} {{}}")
    state_nodes = lambda level_id: [node for node in model.levels[level_id]["nodes"] if node["id"] in world.states[level_id]["region"]]
    for level_id, info in world.states.items():
        regions = {}
        for node in state_nodes(level_id):
            regions.setdefault(info["region"][node["id"]], []).append(identifier(node["label"]))
        for region, state_names in regions.items():
            lines.append(f"var sig {', '.join(state_names)} in {info['subject']} {{}}")

    lines += ["", "-- calls: each step of a run is the set of calls made in it", "abstract sig Call {}", "one sig Now { var happens: set Call }"]
    for kind, fields in world.kinds.items():
        body = ", ".join(f"{k}: {value}" for k, value in fields.items())
        lines.append(f"sig {kind} extends Call {{ {body} }}")
    lines.append("pred stutter { no Now.happens }")

    lines += ["", "-- what happened in this step"]
    done = set()
    for level_id, info in world.states.items():
        subject, labels = info["subject"], {}
        for key, (edge_level, edge) in model.edges.items():
            if edge_level == level_id and key in world.edge_kind:
                labels.setdefault(edge["label"], []).append((key, edge))
        for label, label_edges in labels.items():
            name = world.event_predicate[(level_id, label)]
            if (name, subject) not in done:
                done.add((name, subject))
                froms = " + ".join(sorted({identifier(model.nodes[edge["from"]]["label"]) for _, edge in label_edges}))
                lines.append(f"pred {name}[s: {subject}] {{ some c: Now.happens & {world.edge_kind[label_edges[0][0]]} | c.self = s and s in {froms} }}")

    lines += ["", "-- rules"]
    for rule in document["rules"]:
        lines.append(f"-- {rule['slug']} ({rule['kind']}, {classes[rule['slug']]})")
        lines.append(f"pred {world.rule_name[rule['slug']]} {{\n  " + formula.layout(rule["formula"]).replace("\n", "\n  ") + "\n}")

    def superstate(level_id):
        """The state a state level is opened from, whose instances its states partition, or None."""
        parent = model.parent[level_id]
        # a level of another subject only zooms in, since its instances are not the superstate's
        same = parent and model.node_level[parent] in world.states and world.states[model.node_level[parent]]["subject"] == world.states[level_id]["subject"]
        return identifier(model.nodes[parent]["label"]) if same else None

    behaviour_lines = []
    for level_id, info in world.states.items():
        level, subject = model.levels[level_id], info["subject"]
        regions = {}
        for node in state_nodes(level_id):
            regions.setdefault(info["region"][node["id"]], []).append(node)
        initial_ids = [level["initial"]] if isinstance(level["initial"], str) else level["initial"]
        up = superstate(level_id)
        behaviour_lines.append(f"-- {level['title']}" + (f", inside {up}" if up else ""))
        behaviour_lines.append(f"all s: {up or subject} | " + " and ".join(f"s in {identifier(model.nodes[initial_id]['label'])}" for initial_id in initial_ids))
        for region, nodes in regions.items():
            state_names = [identifier(node["label"]) for node in nodes]
            behaviour_lines.append(f"always ({up or subject} = {' + '.join(state_names)}" + "".join(f" and no {first} & {second}" for position, first in enumerate(state_names) for second in state_names[position + 1:]) + ")")
            if up:   # entering the superstate enters each region at its initial state
                initial_state = next(identifier(model.nodes[initial_id]["label"]) for initial_id in initial_ids if info["region"][initial_id] == region)
                behaviour_lines.append(f"always (all s: {subject} | (s not in {up} and s in {up}') implies s in {initial_state}')")
            pairs = {}
            for key, (edge_level, edge) in model.edges.items():
                if edge_level == level_id and key in world.edge_kind and edge["from"] in {node["id"] for node in nodes}:
                    pairs.setdefault((world.edge_kind[key], identifier(model.nodes[edge["from"]]["label"])), set()).add(identifier(model.nodes[edge["to"]]["label"]))
            for (kind, source), targets in pairs.items():   # leaving the superstate in the same step cuts the event short
                behaviour_lines.append(f"always (all c: Now.happens & {kind} | c.self in {source}{f' and after c.self in {up}' if up else ''} implies after c.self in {' + '.join(sorted(targets))})")
            enable = {}
            for (kind, source) in pairs:
                enable.setdefault(kind, []).append(source)
            for kind, sources in enable.items():   # an event happens only in a state that handles it
                behaviour_lines.append(f"always (all c: Now.happens & {kind} | c.self in {' + '.join(sorted(sources))})")
            moves = [f"(s in {source} and some c: Now.happens & {kind} | c.self = s)" for (kind, source) in pairs]
            moves += [f"(s not in {up} and s in {up}')", f"(s in {up} and s not in {up}')"] if up else []
            same = " and ".join(f"(s in {state_name} iff s in {state_name}')" for state_name in state_names)
            behaviour_lines.append(f"always (all s: {subject} | ({same})" + "".join(f"\n    or {move}" for move in moves) + ")")
        for sync in level.get("syncs", []):
            when, then = world.event_predicate[(level_id, sync["when"])], world.event_predicate[(level_id, sync["then"])]
            where = f" and s in {identifier(model.nodes[sync['where']]['label'])}" if sync.get("where") else ""
            behaviour_lines.append(f"always (all s: {subject} | (s.{when}{where}) implies s.{then})   -- sync {sync['name']}")
    behaviour_lines.append("-- what each transition may change")
    for (owner, attribute), kinds in sorted(world.changed.items()):
        by = " or ".join(f"(some c: Now.happens & {kind} | c.self = x)" if subject == owner else f"some Now.happens & {kind}" for kind, subject in sorted(kinds))
        subset_name = identifier(attribute)
        if world.signatures.get(subset_name, {}).get("of") == owner:
            behaviour_lines.append(f"always (all x: {owner} | (x in {subset_name} iff x in {subset_name}') or {by})")
        else:
            behaviour_lines.append(f"always (all x: {owner} | x.{attribute}' = x.{attribute} or {by})")
    behaviour_lines += [f"always {world.rule_name[rule['slug']]}   -- guard" for rule in document["rules"] if classes[rule["slug"]] == "guard"]
    lines += ["", "-- how things move", "pred behaviour {\n  " + "\n  ".join(behaviour_lines) + "\n}"]

    musts_static = [world.rule_name[rule["slug"]] for rule in document["rules"] if classes[rule["slug"]] == "static" and rule["kind"] == "must"]
    checks = []
    for rule in document["rules"]:   # every rule is asked, a static one under the others, so none is assumed to prove itself
        me = world.rule_name[rule["slug"]]
        given = " and ".join([static_name for static_name in musts_static if static_name != me] + ["behaviour"])
        checks.append((f"holds_{me}", "check", f"{given} implies always {me}", 0 if rule["kind"] == "must" else None, rule["slug"]))
    lines += ["", "-- what Alloy checks"]
    for name, _, body, expected, _ in checks:
        calls = len(world.kinds) + 3   # room for every kind of call at least once, and a few repeats
        lines.append(f"check {name} {{ {body} }} for 3 but {calls} Call, 8 steps" + (f" expect {expected}" if expected is not None else ""))
    return "\n".join(lines) + "\n", world, checks


def _pinned(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() == JAR_SHA256


_checked = {}   # (path, size, mtime) -> whether it matched the pin, so a jar is hashed once per change


def jar():
    """The jar to run: the one PAPERWORK_ALLOY_JAR names, since the owner chose that file, or the cached one when it matches
    the pin. A cached file that does not match is refused (None), as a download would be."""
    named_jar = os.environ.get("PAPERWORK_ALLOY_JAR")
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


def sit_ids(model, slug):
    """The ids of the nodes and edges a rule sits on."""
    return {element_id for _, element_id in model.sits().get(slug, ())}


def trace(world, instances, slug):
    """A counterexample as Schema ids: the nodes whose things witness it, in brackets, then the edges called at each
    step, ` + ` within a step and `|` between edges one call may stand for; where it names neither, the nodes and
    edges the rule sits on."""
    kinds, atom = {}, lambda atom_id: re.sub(r"\$\d+$", "", atom_id)
    for key, kind in world.edge_kind.items():
        kinds.setdefault(kind, set()).add(key)
    signatures = {}
    for node in world.model.nodes.values():
        signatures.setdefault(identifier(node["label"]), node["id"])
    witness = sorted({signatures[atom(cell)] for skolem in (instances[0].get("skolems") or {}).values() for row in skolem.get("data", [])
                      for cell in row if atom(cell) in signatures}) if instances else []
    steps = []
    for instance in instances or []:
        now = next((value for k, value in instance["values"].items() if k.startswith("Now$")), {})
        step = sorted({"|".join(sorted(kinds.get(atom(call[0]), ()))) for call in now.get("happens", [])} - {""})
        if step:
            steps.append(" + ".join(step))
    parts = ([f"[{', '.join(witness)}]"] if witness else []) + ([" → ".join(steps)] if steps else [])
    return " ".join(parts) or ", ".join(sorted(sit_ids(world.model, slug)))

"""Schema checks: the structure a document must hold before Alloy reads it, each problem a sentence saying what to fix."""
import pathlib
import re

from . import formula
from . import prover
from .model import MEMBER, places


def references(model):
    """Every name points at something, so nothing after this asks whether an id exists."""
    out, slugs = [], {rule["slug"] for rule in model.document["rules"]}
    for level_id, level in model.levels.items():
        regions, groups = {region["id"] for region in level.get("regions", [])}, {area["id"] for area in level.get("areas", [])}
        out += [f'{level_id}: {node["id"]} is in no region {node["region"]}' for node in level["nodes"] if "region" in node and node["region"] not in regions]
        out += [f'{level_id}: {node["id"]} is in no area {node["area"]}' for node in level["nodes"] if "area" in node and node["area"] not in groups]
        for element in level["nodes"] + level["edges"]:
            out += [f"{level_id}: {element.get('id', element.get('label'))} names no rule {slug}" for slug in element.get("rules", []) if slug not in slugs]
        out += [f'{level_id}: {edge["label"]} ends on no node {end}' for edge in level["edges"] for end in (edge["from"], edge["to"]) if end not in model.nodes]
    return out


def edge_across_levels(model):
    return [f'{level_id}: {edge["label"]} ends on {end} of another level; write it on the outer level, ending on the opener'
            for level_id, level in model.levels.items() for edge in level["edges"] for end in (edge["from"], edge["to"])
            if end in model.nodes and model.node_level[end] != level_id]


def unique_names(model):
    names = [("node", node["id"]) for level_id, level in model.levels.items() for node in level["nodes"]]
    names += [("node label", re.sub(r"[\s_-]+", " ", node["label"].strip().lower())) for level in model.levels.values() for node in level["nodes"]]
    names += [("rule", rule["slug"]) for rule in model.document["rules"]] + [("scenario", scenario["slug"]) for scenario in model.document["scenarios"]]
    return [f"{kind} {name}: used twice; rename one" for kind, name in sorted(set(names)) if names.count((kind, name)) > 1]


def steps(model):
    out = []
    for scenario in model.document["scenarios"]:
        out += model.walk(scenario)[1]
        out += [f'{scenario["slug"]}: step {index + 1} says what it does and what it expects' for index, step in enumerate(scenario["walk"]) if not step["does"].strip() or not step["expects"].strip()]
        out += [f'{scenario["slug"]}: step {index + 1} is at several nodes, so they are parts of one level' for index, step in enumerate(scenario["walk"]) if len({model.node_level.get(place) for place in places(step)}) > 1]
    return out


def four_states(model):
    """Each region holds every subject instance in exactly one state (Koppel's four states)."""
    out = []
    for level_id, level in model.levels.items():
        states = [node for node in level["nodes"] if node["id"] in model.states(level_id)]
        if not states:
            continue
        side = {node["id"]: node.get("region") or "the level" for node in states}
        initial_states = [level["initial"]] if isinstance(level.get("initial"), str) else level.get("initial") or []
        transitions = [edge for edge in level["edges"] if edge["kind"] == "transition"]
        for region in sorted(set(side.values())):
            count = sum(1 for initial_state in initial_states if side.get(initial_state) == region)
            if count != 1:
                out.append(f'{level_id}: {"Missing" if not count else "Overloaded"}: an instance starts in {count} states of {region}; name one initial state there')
        out += [f'{level_id}: Missing: event {edge["label"]} leaves its region; regions meet only through syncs' for edge in transitions if side[edge["from"]] != side[edge["to"]]]
        seen, todo = set(), list(initial_states)
        while todo:
            seen.add(todo[-1])
            todo = todo[:-1] + [edge["to"] for edge in transitions if edge["from"] == todo[-1] and edge["to"] not in seen]
        out += [f'{level_id}: Illegal: no event reaches {node["id"]}; add the event that enters it, or drop it' for node in states if node["id"] not in seen]
        groups = {}
        for node in states:
            end = lambda node_id: "itself" if node_id == node["id"] else node_id
            exits = frozenset((edge["label"], end(edge["to"])) for edge in transitions if edge["from"] == node["id"])
            entries = frozenset((edge["label"], end(edge["from"])) for edge in transitions if edge["to"] == node["id"])
            groups.setdefault((side[node["id"]], exits, entries, frozenset(node.get("rules", [])), "opens" in node, node["id"] in initial_states), []).append(node["id"])
        out += [f'{level_id}: Redundant: no event or rule tells {" and ".join(members)} apart; merge them or give each its own' for members in groups.values() if len(members) > 1]
    return out


def syncs(model):
    out = []
    for level_id, level in model.levels.items():
        region = {node["id"]: node.get("region") for node in level["nodes"]}
        events = {edge["label"]: region.get(edge["from"]) for edge in level["edges"] if edge["kind"] == "transition"}
        for sync in level.get("syncs", []):
            known = sync["when"] in events and sync["then"] in events and sync.get("where", next(iter(region), None)) in region
            joins = known and events[sync["when"]] is not None and events[sync["when"]] != events[sync["then"]]
            out += [] if joins else [f'{level_id}: sync {sync["name"]}: when and then name events of two regions of this level, and where a state of it']
    return out


def area_links(model):
    """Each area of each level with its nodes, and for each edge how many of its ends fall inside."""
    for level_id, level in model.levels.items():
        for area in level.get("areas", []):
            inside = {node["id"] for node in level["nodes"] if node.get("area") == area["id"]}
            yield level_id, area, inside, [(edge["from"] in inside) + (edge["to"] in inside) for edge in level["edges"]]


def area_size(model):
    return [f'{level_id}: area {area["id"]} holds {len(inside)} node; an area needs two' for level_id, area, inside, _ in area_links(model) if len(inside) < 2]


def area_cohesion(model):
    return [f'{level_id}: area {area["id"]} has {ends.count(2)} links inside and {ends.count(1)} outside; give it a unit or drop it'
            for level_id, area, inside, ends in area_links(model) if len(inside) >= 2 and ends.count(2) <= ends.count(1) and not area.get("unit")]


def typed(model):
    out = list(prover.World(model).problems)
    for level_id, level in model.levels.items():
        out += [f'{node["label"]}: attribute "{attribute}" is name: Type on a part' for node in level["nodes"] for attribute in node.get("attrs", [])
                if node["id"] in model.states(level_id) or not re.fullmatch(rf"{MEMBER}\s*:\s*.+", attribute)]
        out += [f'{level_id}: {edge["label"]} names attribute {edge["attr"]}, which {edge["from"]} does not have' for edge in level["edges"]
                if edge.get("attr") and not any(attribute.split(":")[0].strip() == edge["attr"] for attribute in model.nodes[edge["from"]].get("attrs", []))]
    return out


def vocabulary(model):
    """Formulas and names, caught here before the slow Alloy run."""
    world = prover.World(model)
    out = [problem for rule in model.document["rules"] for problem in world.check_formula(rule["formula"], rule["slug"])]
    declared = list(world.signatures) + list(world.fields) + list(world.predicates) + list(world.atoms)
    out += [f'"{name}" is a word Alloy or the translation reserves; rename it' for name in declared if name in formula.RESERVED]
    out += [f'"{name}" gives no Alloy name; write it in ASCII letters' for name in declared if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name)]
    return out


def cited(model):
    return [element["meta"]["source"] for level in model.levels.values() for element in level["nodes"] + level["edges"]] + [rule["meta"]["source"] for rule in model.document["rules"]]


def source_mixed(model):
    urls = sum("://" in source for source in cited(model))
    return [f"{urls} of {len(cited(model))} sources are urls; a url stands only for a system known solely from web documents"] if 0 < urls < len(cited(model)) else []


def inside_its_file(source, root):
    target, lines = pathlib.Path(root) / source.rpartition(":")[0], [int(line) for line in source.rpartition(":")[2].split("-")]
    return target.is_file() and 0 < lines[0] <= lines[-1] <= len(target.read_text(encoding="utf-8", errors="replace").splitlines())


def source_unresolved(model, root):
    return [f"{source} is past the end of its file, or no such file under {root}" for source in sorted(set(cited(model))) if "://" not in source and not inside_its_file(source, root)]


RULES = [
    ("reference", references, "every name points at something"), ("edge-across-levels", edge_across_levels, "an edge joins two nodes of one level"),
    ("unique-names", unique_names, "no two things share a name"), ("steps", steps, "every step says what it does and expects, and follows an edge or opens or closes a level"),
    ("four-states", four_states, "each region holds an instance in one state: one initial state, events kept in the region, every state reached, no two alike"), ("syncs", syncs, "regions meet only through syncs, each joining events of two regions"),
    ("area-size", area_size, "an area holds at least two nodes"), ("area-cohesion", area_cohesion, "an area has more links inside than outside, or a unit"),
    ("typed", typed, "types are names the module declares, attributes sit on parts"), ("vocabulary", vocabulary, "formulas are Alloy over the document's names, and every name is an Alloy name"),
    ("source-mixed", source_mixed, "a url source stands only for a system with no file to cite"),
]
UNRESOLVED = "with --root, each path:line points inside its file"


def violations(model, root=None):
    """Every problem as (rule, sentence). The first two rules stop the rest, which read the model through what they guard."""
    rows = []
    for index, (name, check, _) in enumerate(RULES):
        rows += [(name, problem) for problem in check(model)]
        if index == 1 and rows:
            return rows
    return rows + [("source-unresolved", problem) for problem in (source_unresolved(model, root) if root else [])]

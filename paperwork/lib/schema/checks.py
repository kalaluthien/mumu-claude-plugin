"""Schema checks: each takes a Model and returns the problems it found, each a sentence that says what to fix, or a
(rule, sentence) pair when it states a narrower rule than the check's own."""
import re

from . import formula
from . import plan as plan_module
from . import prover
from . import sources as source_files
from .model import MEMBER, places, plan, split_top, walk_steps

NODE_MEDIA, EDGE_MEDIA = {"tree", "checklist"}, {"diff", "payload"}
first_word = lambda text: text.strip().split()[0].lower() if text and text.strip() else ""
plain_verb = lambda word: not ((word.endswith("ed") and not word.endswith("eed")) or word.endswith("ing") or (word.endswith("s") and not word.endswith("ss")))


def form(model):
    """The file read as a model: every reference points at something (model.parse), and the plan holds together."""
    return model.parse_problems + plan_module.problems(model.document, [rule[0] for rule in RULES])


def steps(model):
    out = []
    for scenario in model.document["scenarios"]:
        for index, step in enumerate(walk_steps(scenario["walk"])):
            if not (isinstance(step, dict) and str(step.get("does", "")).strip() and str(step.get("expects", "")).strip()):
                out.append(f'{scenario["slug"]}: step {index + 1} says what it does and what it expects ({{"place", "does", "expects"}})')
            elif len(places(step)) > 1 and not all(model.kind_of.get(place) == "topology" and model.node_level.get(place) == model.node_level.get(places(step)[0]) for place in places(step)):
                out.append(f'{scenario["slug"]}: step {index + 1} is at several nodes, so they are parts of one component level')
        out += model.walks[scenario["slug"]][1]
    return out


def scoped(model):
    out = []
    for slug, home in model.home.items():
        scenario = next(candidate for candidate in model.document["scenarios"] if candidate["slug"] == slug)
        climb = [place for place in plan(scenario["walk"])[0] if place in model.nodes and home not in model.ancestors(model.node_level[place])]
        if climb:
            out.append(f'{slug}: starts in {home} but climbs above it at {climb[0]}')
    # every level needs Scenarios of its own, or (plan scenarios: entry) only the root and levels things enter from outside
    own = [level for level in model.document["levels"] if model.plan["scenarios"] == "every" or not level.get("parent") or level.get("triggers")]
    out += [f'{level["id"]}: give this level a Scenario of its own' for level in own if level["id"] not in model.home.values()]
    return out


def coverage(model):
    used = set().union(*model.footprint.values()) if model.footprint else set()
    orphans = sorted(model.elements() - used)
    return [f"no Scenario uses {kind} {name}; drop it or name the use it serves" for kind, name in orphans]


def basis(model):
    out = []
    for slug, elements in model.footprint.items():
        subsets = [other for other, other_elements in model.footprint.items() if other != slug and other_elements <= elements and model.home.get(other) == model.home.get(slug)]
        if subsets and set().union(*(model.footprint[other] for other in subsets)) == elements:
            out.append(f"{slug} is the union of {subsets}; drop it")
    return out


def placement(model):
    out = []
    event_operations = {operation for level in model.document["levels"] if level["kind"] == "state" for edge in level["edges"] + level.get("triggers", []) for operation in edge.get("ops", [])}
    edge_operations = {operation for _, edge in list(model.edges.values()) + list(model.triggers.values()) for operation in edge.get("ops", [])}
    sits = model.sits()
    for slug in model.operations:
        if slug not in sits:
            out.append(f"{slug}: place it on a node or an event")
        elif slug in edge_operations - event_operations:
            out.append(f"{slug}: only an event edge carries an operation")
    out += [f"{rule_slug}: place it on a node or an edge" for rule_slug in model.rules if rule_slug not in sits]
    return out


def explained(model):
    out = []
    for k, (level, edge) in model.edges.items():
        if not (edge.get("what") or edge.get("ops") or edge.get("rules") or model.is_abstract(level, edge["to"])):
            out.append(f'{level["id"]}: {edge["from"]}>{edge["to"]} says nothing; give it a sentence, an operation or a guard')
    for k, (level, trigger) in model.triggers.items():
        if not (trigger.get("what") or trigger.get("ops") or trigger.get("rules")):
            out.append(f'{level["id"]}: trigger {trigger["label"]} says nothing')
    return out


def mechanism(model):
    out = []
    walks = lambda visited: any(model.kind_of.get(place) in ("workflow", "state") for place in visited)
    if not any(level["kind"] in ("workflow", "state") for level in model.document["levels"]):
        return out   # nothing runs: a body of knowledge is claims and what they rest on
    rooted = [scenario for scenario in model.document["scenarios"] if model.home.get(scenario["slug"]) == model.root]
    out += [f'{scenario["slug"]}: a root Scenario walks no activity or state' for scenario in rooted if not walks(plan(scenario["walk"])[0])]
    parts = [place for place, kind in model.kind_of.items() if kind == "topology"]
    if not parts:
        out.append("no component level: show what the system is made of")
    out += [f"{place}: in no root Scenario that also walks an activity or state" for place in parts
            if not any(place in plan(scenario["walk"])[0] and walks(plan(scenario["walk"])[0]) for scenario in rooted)]
    return out


def partitions(model):
    out = []
    for level in model.document["levels"]:
        partition_ids = {partition["id"] for partition in level.get("partitions", [])}
        if not partition_ids:
            continue
        if len(partition_ids) < 2:
            out.append(f'{level["id"]}: one partition says nothing; drop it')
        out += [f'{level["id"]}: put {node["id"]} in a partition' for node in level["nodes"] if node.get("partition") not in partition_ids]
        side = {node["id"]: node.get("partition") for node in level["nodes"]}
        if level["kind"] == "state":   # its partitions are orthogonal regions (Harel), which four-states checks
            continue
        for edge in level["edges"]:
            contract = edge.get("rules") or edge.get("ops") or any(medium.get("type") == "payload" for medium in edge.get("media", []))
            if level["kind"] != "topology" and side.get(edge["from"]) != side.get(edge["to"]) and not contract:
                out.append(f'{level["id"]}: {edge["from"]}>{edge["to"]} crosses partitions; give it a payload, guard or operation')
    return out



def four_states(model):
    """Each region of a state level holds every subject instance in exactly one state (Koppel's four states:
    https://note89.github.io/state-of-emergency/): one initial state, events that stay in the region, every state
    reached, and no two states alike."""
    out = []
    for level in model.document["levels"]:
        if level["kind"] != "state":
            continue
        level_id, side = level["id"], {node["id"]: node.get("partition") or "the level" for node in level["nodes"]}
        initial_states = [level["initial"]] if isinstance(level.get("initial"), str) else level.get("initial") or []
        for region in sorted(set(side.values())):
            count = sum(1 for initial_state in initial_states if side.get(initial_state) == region)
            if count == 0:
                out.append(("region-without-initial", f"{level_id}: Missing: an instance starts in no state of {region}; name one initial state there"))
            elif count > 1:
                out.append(f"{level_id}: Overloaded: an instance starts in {count} states of {region} at once; keep one initial state")
        out += [f'{level_id}: Missing: event {edge["label"]} leaves its region, so the instance is in no state of {side[edge["from"]]}; regions meet only through syncs'
                for edge in level["edges"] if side.get(edge["from"]) != side.get(edge["to"])]
        seen, todo = set(), list(initial_states) + [trigger["to"] for trigger in level.get("triggers", [])]
        while todo:
            state = todo.pop()
            if state not in seen:
                seen.add(state)
                todo += [edge["to"] for edge in level["edges"] if edge["from"] == state]
        # a region with no initial state is one fault, already reported, not one per state it leaves unreached
        started = {side.get(initial_state) for initial_state in initial_states}
        out += [f'{level_id}: Illegal: no event reaches {node["id"]}; add the event that enters it, or drop it' for node in level["nodes"]
                if node["id"] not in seen and side[node["id"]] in started]
        def alike(node):
            end = lambda node_id: "itself" if node_id == node["id"] else node_id
            return (side[node["id"]], frozenset((edge["label"], end(edge["to"])) for edge in level["edges"] if edge["from"] == node["id"]),
                    frozenset((edge["label"], end(edge["from"])) for edge in level["edges"] if edge["to"] == node["id"]),
                    frozenset(node.get("ops") or []), frozenset(node.get("rules") or []), node["id"] in initial_states)
        groups = {}
        for node in level["nodes"]:
            groups.setdefault(alike(node), []).append(node["id"])
        out += [f'{level_id}: Redundant: no event or rule tells {" and ".join(members)} apart; merge them or give each its own' for members in groups.values() if len(members) > 1]
    return out

GATES = {"checking", "reviewing", "validating", "verifying", "testing", "judging", "approving", "gating", "evaluating"}


def quantities(model):
    """Quantities add up: a count is what enters and what leaves it, a node that holds nothing passes on what it
    receives, a flow into or out of a stock is in the stock's unit, and a deadline says what happens when it passes."""
    out, same = [], lambda left, right: abs(left - right) <= 1e-9 * max(1, abs(left), abs(right))
    for level in model.document["levels"]:
        for edge in level["edges"]:
            quantity = edge.get("qty")
            if quantity and quantity["kind"] not in ("flow", "count", "delay"):
                out.append(f'{level["id"]}: {edge["label"]} carries a flow, a count or a delay, not a {quantity["kind"]}')
            if quantity and quantity["kind"] == "delay" and not any(other is not edge and other["from"] == edge["from"] and "failure" in other.get("mark", []) for other in level["edges"]):
                out.append(f'{level["id"]}: {edge["label"]} has a deadline; draw what happens when it passes, an edge from {edge["from"]} marked failure')
        for node in level["nodes"]:
            quantity = node.get("qty")
            if quantity and quantity["kind"] not in ("stock", "count", "capacity"):
                out.append(f'{level["id"]}: {node["label"]} holds a stock, a count or a capacity, not a {quantity["kind"]}')
                continue
            sides = {"in": [side_edge for side_edge in level["edges"] if side_edge["to"] == node["id"] != side_edge["from"]],
                     "out": [side_edge for side_edge in level["edges"] if side_edge["from"] == node["id"] != side_edge["to"]]}
            if quantity and quantity["kind"] == "stock":
                out += [f'{level["id"]}: {side_edge["label"]} moves {side_edge["qty"]["unit"]}, not the {quantity["unit"]} that {node["label"]} holds'
                        for edges in sides.values() for side_edge in edges
                        if edge.get("qty", {}).get("kind") == "flow" and "unit" in edge["qty"] and "unit" in quantity
                        and edge["qty"]["unit"].split("/")[0].strip() != quantity["unit"]]
                continue
            told = {k: [side_edge["qty"] for side_edge in edges if side_edge.get("qty", {}).get("kind") in ("flow", "count")] for k, edges in sides.items()}
            full = {k: flows for k, flows in told.items() if flows and len(flows) == len(sides[k]) and len({flow.get("unit", "") for flow in flows}) == 1}
            total = {k: sum(flow["value"] for flow in flows) for k, flows in full.items()}
            if quantity and quantity["kind"] == "count":
                out += [f'{level["id"]}: {node["label"]} counts {quantity["value"]}, but {total[k]} {"enter" if k == "in" else "leave"}'
                        for k in total if not same(total[k], quantity["value"])]
            elif len(total) == 2 and full["in"][0].get("unit", "") == full["out"][0].get("unit", "") and not same(total["in"], total["out"]):
                out.append(f'{level["id"]}: {node["label"]} holds nothing, yet {total["in"]} enter and {total["out"]} leave')
    return out


def paths(model):
    """A workflow or state level shows its main path, and every gate shows how it fails."""
    out = []
    for level in model.document["levels"]:
        if level["kind"] == "topology":
            continue
        if not any("happy" in edge.get("mark", []) for edge in level["edges"]):
            out.append(f'{level["id"]}: mark the main path happy')
        parent = level.get("parent") and model.level_of(level["parent"])
        port_fail = {source for port in level.get("out", []) for source in ([port["from"]] if isinstance(port.get("from"), str) else port.get("from", []))
                     if parent and any(edge["label"] == port.get("edge") and "failure" in edge.get("mark", []) for edge in parent["edges"])}
        for node in level["nodes"]:
            if first_word(node["label"]) in GATES:
                fails = any(edge["from"] == node["id"] and "failure" in edge.get("mark", []) for edge in level["edges"]) or node["id"] in port_fail
                if not fails:
                    out.append(f'{level["id"]}: {node["label"]} is a gate; draw how it fails (a failure edge or port)')
    return out


def syncs(model):
    """Regions meet only through syncs (Meng and Jackson): when an event in one region, where a state holds, then an event in another."""
    out = []
    for level in model.document["levels"]:
        region = {node["id"]: node.get("partition") for node in level["nodes"]}
        events = {edge["label"]: region.get(edge["from"]) for edge in level["edges"]}
        for sync in level.get("syncs", []):
            name = sync.get("name", "?")
            if level["kind"] != "state" or not level.get("partitions"):
                out.append(f'{level["id"]}: sync {name} joins regions, so it sits on a state level with partitions')
            elif events[sync["when"]] == events[sync["then"]]:
                out.append(f'{level["id"]}: sync {name} joins two events of one region; join regions')
            if not sync.get("what"):
                out.append(f'{level["id"]}: sync {name} says nothing; give it a sentence')
    return out


def naming(model):
    out = []
    for level in model.document["levels"]:
        kind = level["kind"]
        for node in level["nodes"]:
            if kind == "workflow" and not first_word(node["label"]).endswith("ing"):
                out.append(f'{level["id"]}: activity "{node["label"]}" starts with a verb in -ing')
            if node.get("abstract") and kind != "topology":
                out.append(f'{level["id"]}: only a component can be abstract')
        for edge in level["edges"]:
            word = first_word(edge.get("label", ""))
            if kind == "topology" and not word.endswith("s"):
                out.append(f'{level["id"]}: relation "{edge["label"]}" starts with a present-tense verb (uses, opens)')
            if kind == "state" and not plain_verb(word):
                out.append(f'{level["id"]}: event "{edge["label"]}" starts with a plain verb (merge, mark ready)')
            if kind == "workflow" and word.endswith("ing") and not edge.get("is"):
                out.append(f'{level["id"]}: artifact "{edge["label"]}" is a noun phrase')
            if model.is_abstract(level, edge["from"]) and not model.is_abstract(level, edge["to"]):
                out.append(f'{level["id"]}: abstract {edge["from"]} cannot depend on concrete {edge["to"]}')
        for trigger in level.get("triggers", []):
            word = first_word(trigger.get("label", ""))
            if (kind == "state" and not plain_verb(word)) or (kind == "workflow" and word.endswith("ing")):
                out.append(f'{level["id"]}: trigger "{trigger["label"]}" is named like the level\'s edges')
        for element in level["nodes"] + level["edges"] + level.get("triggers", []):
            if {"happy", "failure"} <= set(element.get("mark", [])):
                out.append(f'{level["id"]}: {element.get("label")} is marked both happy and failure')
    return out


def media(model):
    out = []
    words = lambda text: set(re.findall(r"\w{2,}", text))
    for level in model.document["levels"]:
        hosts = [(node, "node") for node in level["nodes"]] + [(edge, "edge") for edge in level["edges"]] + [(level, "level")]
        insights = 0
        for host, where in hosts:
            for medium in host.get("media", []):
                kind = medium.get("type")
                if (kind in NODE_MEDIA and where == "edge") or (kind in EDGE_MEDIA and where == "node"):
                    out.append(f'{level["id"]}: {kind} does not sit on a {where}')
                if kind != "insight":
                    continue
                insights += 1
                here = set(model.operations) | set(model.rules) if where == "level" else set(host.get("ops", [])) | set(host.get("rules", []))
                missing_fields = [field for field in ("move", "vs", "gain", "rule") if not str(medium.get(field, "")).strip()]
                move, description = words(medium.get("move", "")), words(host.get("what", host.get("why", "")))
                if missing_fields:
                    out.append(f'{level["id"]}: an insight needs move, vs, gain and rule (missing {missing_fields})')
                elif medium["rule"] not in here:
                    out.append(f'{level["id"]}: the insight\'s rule {medium["rule"]} must sit on the same node or edge')
                elif move and len(move & description) / len(move) > 0.5:
                    out.append(f'{level["id"]}: an insight names what is distinctive, not what the description says')
        if insights > 1:
            out.append(f'{level["id"]}: {insights} insights; keep the most distinctive one')
    return out


def unique_names(model):
    document = model.document
    normalize = lambda text: re.sub(r"[\s_-]+", " ", text.strip().lower())
    linked = {(level["id"], edge["label"]) for level in document["levels"] for edge in level["edges"] if edge.get("is")}
    names = ([("scenario", scenario["slug"]) for scenario in document["scenarios"]] + [("operation", operation["slug"]) for operation in document["operations"]]
             + [("rule", rule["slug"]) for rule in document["rules"]] + [("level", level["title"]) for level in document["levels"]]
             + [("node", node["label"]) for node in model.nodes.values()]
             + [("partition", label) for label in {partition["label"] for level in document["levels"] for partition in level.get("partitions", [])}]   # one owner may recur across levels
             + [("edge", label) for label in {edge["label"] for level in document["levels"] for edge in level["edges"]   # a verb may recur
                                          if edge.get("label") and not model.is_abstract(level, edge["to"]) and (level["id"], edge["label"]) not in linked}]
             + [("trigger", trigger["label"]) for level in document["levels"] for trigger in level.get("triggers", [])]
             + [("sync", sync["name"]) for level in document["levels"] for sync in level.get("syncs", []) if sync.get("name")])
    seen, out = {}, []
    for kind, name in names:
        seen.setdefault(normalize(name), []).append(f"{kind} '{name}'")
    out += [" = ".join(entries) + "; rename one" for entries in seen.values() if len(entries) > 1]
    for level in document["levels"]:
        for edge in level["edges"]:
            target = model.nodes.get(edge.get("is"))
            if edge.get("is") and not (level["kind"] == "workflow" and target and model.kind_of[edge["is"]] == "topology" and prover.singular(prover.identifier(target["label"])) == prover.singular(prover.identifier(edge["label"]))):
                out.append(f'{level["id"]}: {edge["from"]}>{edge["to"]} "is" names a component with the same label')
    return out


def typed(model):
    """Types are exact names the module declares; signatures, attributes and relations agree with the drawing."""
    world = prover.World(model)
    out = list(world.problems)
    for type_name, text in (model.document.get("types") or {}).items():
        if not re.sub(r"^\s*\{[^}]*\}", "", str(text)).strip():
            out.append(f"type {type_name}: say in a sentence what it is")
    for operation in model.document["operations"]:
        slug = operation["slug"]
        if slug not in model.signatures:
            out.append(f'{slug}{operation.get("sig", "")}: write Receiver.verb and (name: Type, …) → Result')
            continue
        parameters = split_top(re.match(r"\s*\((.*)\)", operation["sig"]).group(1))
        out += [f"{slug}: parameter {parameter} needs name: Type" for parameter in parameters if not re.fullmatch(rf"{MEMBER}\s*:\s*.+", parameter)]
    for level in model.document["levels"]:
        for node in level["nodes"]:
            operation_slugs = [operation_slug for operation_slug in node.get("ops", []) if operation_slug in model.signatures]
            if level["kind"] == "topology":
                out += [f'{level["id"]}: {operation_slug} sits on {node["label"]}, so its receiver is {prover.identifier(node["label"])}' for operation_slug in operation_slugs if model.signatures[operation_slug][0] != prover.identifier(node["label"])]
            if level["kind"] == "workflow" and operation_slugs:
                outgoing_labels = [edge["label"] for edge in level["edges"] if edge["from"] == node["id"]]
                made = {reference for operation_slug in operation_slugs for reference in prover.Type(re.search(r"→\s*(.+)$", model.operations[operation_slug]["sig"]).group(1)).references()}
                if outgoing_labels and not any(made & prover.artifact_types(label) for label in outgoing_labels):
                    out.append(f'{level["id"]}: {node["label"]} hands on {", ".join(outgoing_labels)}, but none of its operations returns it')
            for attribute in node.get("attrs", []):
                parsed = re.fullmatch(rf"({MEMBER})\s*:\s*(.+)", attribute)
                if not parsed or level["kind"] != "topology":
                    out.append(f'{node["label"]}: attribute "{attribute}" is name: Type on a component')
        if level["kind"] != "topology":
            continue
        components = {prover.identifier(component["label"]): component for component in level["nodes"]}
        attributes = {component["id"]: [(attribute_name, attribute_type) for _, owner, attribute_name, attribute_type in world._attributes() if owner is component] for component in level["nodes"]}
        for node in level["nodes"]:
            for member_name, member_type in attributes[node["id"]]:
                peers = [components[peer_name] for peer_name in member_type.names if len(member_type.names) == 1 and not member_type.tuple and peer_name in components and components[peer_name] is not node and not components[peer_name].get("abstract")]
                for peer in peers:
                    if not any(edge["from"] == node["id"] and edge["to"] == peer["id"] for edge in level["edges"]):
                        out.append(f'{node["label"]}.{member_name} points at {peer["label"]}; draw the relation')
        for edge in level["edges"]:
            if model.is_abstract(level, edge["to"]):
                continue
            to = prover.identifier(model.nodes[edge["to"]]["label"])
            candidates = [attribute_name for attribute_name, attribute_type in attributes[edge["from"]] if to in attribute_type.references()]
            if edge.get("attr"):
                if edge["attr"] not in candidates:
                    out.append(f'{level["id"]}: relation {edge["label"]} names attribute {edge["attr"]}, which does not point at {model.nodes[edge["to"]]["label"]}')
            elif len(candidates) > 1:
                out.append(f'{level["id"]}: relation {edge["label"]} could be {candidates}; name one with attr')
    return out


def alloy_names(model):
    """Every name the module declares is an Alloy name (ASCII, starting with a letter) clear of Alloy's keywords
    and the translation's own words; caught here, before the slow Alloy run."""
    document, found = model.document, []
    for level in document["levels"]:
        found += [(prover.identifier(node["label"]), node["label"]) for node in level["nodes"]]
        found += [(prover.lower(element["label"]), element["label"]) for element in level["edges"] + level.get("triggers", []) if level["kind"] == "state" and element.get("label")]
        found += [((prover.identifier if attribute.split(":", 1)[-1].strip() == "Bool" else str)(attribute.split(":")[0].strip()), attribute) for node in level["nodes"] for attribute in node.get("attrs", [])]
        found += [(prover.lower(edge["label"]), edge["label"]) for edge in level["edges"] if level["kind"] in ("topology", "workflow") and edge.get("label")]
        if level["kind"] == "workflow":
            found.append((prover.identifier(level["title"]), level["title"]))
    for operation in document["operations"]:
        if operation["slug"] in model.signatures:
            found.append((model.signatures[operation["slug"]][2], operation["slug"]))
            found += [(parameter, operation["slug"]) for parameter in model.signatures[operation["slug"]][1]]
    found += [(prover.lower(rule["slug"]), rule["slug"]) for rule in document["rules"]]
    found += [(type_name, type_name) for type_name in (document.get("types") or {})]
    for text in [attribute for level in document["levels"] for node in level["nodes"] for attribute in node.get("attrs", [])] + [declaration.get("sig", "") for declaration in document["operations"]] + list((document.get("types") or {}).values()):
        for literal in re.findall(r"\{([^}]*)\}", str(text)):
            found += [(item.strip(), literal) for item in literal.split(",")]
    out = {f'"{name}" in {where} is a word Alloy or the translation reserves; rename it' for name, where in found if name in formula.RESERVED}
    out |= {f'{where} gives no Alloy name ("{name}"); write it in ASCII letters' for name, where in found if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", str(name))}
    return sorted(out)


def vocabulary(model):
    """Formulas are Alloy over the module's names, with every variable bound and no name hidden; every name is an
    Alloy name (alloy_names)."""
    world, out = prover.World(model), alloy_names(model)
    for rule in model.document["rules"]:
        out += world.check_formula(rule["formula"], rule["slug"])
    for slug, operation in list(world.change.items()) + list(world.query.items()):
        extra = ["self"] + [parameter for parameter, _, _ in operation["params"]] + (["result"] if operation["rdecl"] else [])
        for part in ("pre", "post"):
            if operation.get(part):
                out += world.check_formula(operation[part], f"{slug} {part}", extra)
    for level in model.document["levels"]:
        if level.get("init"):
            out += world.check_formula(level["init"], f'{level["id"]} init')
    return out


def opens(model):
    """Zoom as refinement: an unmarked same-kind open keeps its node's interface, every edge into or out of the node
    a port of the child (a state child takes them at its initial state); a kind change is a view link, marked view;
    a same-kind open with no interface claim is marked nest, and warned."""
    out = []
    for level in model.document["levels"]:
        parent_node = level.get("parent") and model.nodes[level["parent"]]
        if not parent_node:
            continue
        parent_level, link = model.level_of(parent_node["id"]), parent_node.get("link")
        if parent_level["kind"] != level["kind"]:
            out += [] if link == "view" else [("view-link-unmarked", f'{parent_node["id"]}: opens a {level["kind"]} level from a {parent_level["kind"]} level; mark it link: view')]
        elif link == "view":
            out.append(("form", f'{parent_node["id"]}: a view link changes kind; a same-kind open is unmarked or nest'))
        elif link == "nest":
            out.append(("nest-unrefined", f'{parent_node["id"]}: nests a {level["kind"]} level with no interface claim; map its edges onto ports to refine it'))
        elif level["kind"] != "state":
            ids = {node["id"] for node in level["nodes"]}
            # lists, not sets: two parent edges may share a label, and each needs its own port
            need_in = sorted([edge["label"] for edge in parent_level["edges"] if edge["to"] == parent_node["id"]] + [trigger["label"] for trigger in parent_level.get("triggers", []) if trigger["to"] == parent_node["id"]])
            need_out = sorted([edge["label"] for edge in parent_level["edges"] if edge["from"] == parent_node["id"]])
            got_in = sorted(port.get("edge") for port in level.get("in", []) if port.get("to") in ids)
            got_out = sorted(port.get("edge") for port in level.get("out", []) if port.get("from") and set([port["from"]] if isinstance(port["from"], str) else port["from"]) <= ids)
            if (got_in, got_out) != (need_in, need_out):
                out.append(("opens-interface", f'{level["id"]}: in {got_in} should be {need_in}; out {got_out} should be {need_out}'))
    return out


def gates(model):
    """A workflow forks into branches that run side by side and joins them again: a fork has two or more edges out, a
    join two or more in, and every join has a fork before it on its level."""
    out = []
    for level in model.document["levels"]:
        for node in level["nodes"]:
            gate = node.get("gate")
            if gate and level["kind"] != "workflow":
                out.append(("form", f'{node["id"]}: only a workflow step is a {gate}'))
                continue
            incoming = [edge["from"] for edge in level["edges"] if edge["to"] == node["id"]]
            outgoing = [edge["to"] for edge in level["edges"] if edge["from"] == node["id"]]
            if gate == "fork" and len(outgoing) < 2:
                out.append(("gates", f'{node["id"]}: a fork has two or more edges out'))
            if gate == "join":
                def above(start):
                    seen, todo = set(), [start]
                    while todo:
                        current = todo.pop()
                        if current not in seen:
                            seen.add(current)
                            todo += [edge["from"] for edge in level["edges"] if edge["to"] == current]
                    return {node_id for node_id in seen if model.nodes[node_id].get("gate") == "fork"}
                # one fork must lie above every edge in, so each comes from one of its branches
                if len(incoming) < 2 or not set.intersection(*map(above, incoming)):
                    out.append(("join-without-fork", f'{node["id"]}: a join has two or more edges in, from branches of a fork before it'))
    return out


def sources(model):
    out, model.sources_status = source_files.problems(model.document)
    return out


LINT = {"basis", "explained", "mechanism", "paths", "naming", "media", "nest-unrefined"}

RULES = [
    ("form", "the file is well formed: one root, known kinds, initial states, named edges, refs as [name](url) or [name](path:line), a valid plan", form),
    ("steps", "every Scenario step says what it does and expects, and follows an edge or opens or closes a level", steps),
    ("scoped", "the root and every level things enter from outside have Scenarios of their own (plan scenarios: every asks it of all); steps never climb above where they start", scoped),
    ("coverage", "every operation, rule, node, edge and trigger is used by some Scenario", coverage),
    ("basis", "no Scenario is the union of other Scenarios on its level", basis),
    ("placement", "operations sit on nodes or events, rules on nodes or edges", placement),
    ("explained", "every edge and trigger says something: a sentence, an operation or a guard", explained),
    ("mechanism", "where anything runs, root Scenarios walk an activity or state, and every component meets one of them", mechanism),
    ("partitions", "every node of a partitioned level is in one of two or more partitions, crossings carry a contract (render checks the blocks)", partitions),
    ("quantities", "counts and pass-through nodes add up, flows match their stock's unit, every deadline shows what happens when it passes", quantities),
    ("paths", "a workflow or state level marks its main path, and every gate (checking, reviewing, …) shows how it fails", paths),
    ("four-states", "each region of a state level holds an instance in one state: one initial state, events kept in the region (not Missing or Overloaded), every state reached (not Illegal), no two states alike (not Redundant)", four_states),
    ("syncs", "regions of a state level meet only through syncs: when an event, where a state, then an event in another region", syncs),
    ("naming", "labels follow their kind; abstract components depend only on abstract ones; marks are known", naming),
    ("media", "media sit where its type allows; an insight names a move, the usual design, the gain and a rule", media),
    ("unique-names", "no two things the reader sees share a name", unique_names),
    ("typed", "types are names the module declares; signatures, attributes and relations agree with the drawing", typed),
    ("vocabulary", "every name is an ASCII Alloy name clear of Alloy's keywords and the translation's words; formulas are Alloy over the model's names, every variable bound and none hiding a name", vocabulary),
    ("opens", "an unmarked same-kind open carries every edge of its node on ports or at the initial state; a kind change is marked view; a nest is warned", opens),
    ("gates", "a fork has two or more edges out, a join two or more in from branches of a fork before it", gates),
    ("sources", "with plan.sources: each listed file is cited by a ref, each cited file is listed, and (closure) every file inside the root a listed file links to, imports or names as ${CLAUDE_PLUGIN_ROOT}/<path> is listed or excluded with a one-line reason", sources),
]
CHECKS = {rule[0] for rule in RULES}


def unknown(only, known):
    """The refusal for a check name nobody runs, naming the known ones; None when every name is known."""
    bad = [name for name in only or [] if name not in known and name != "form"]
    return f"unknown check {', '.join(bad)}; known: {', '.join(sorted(known | {'form'}))}" if bad else None


def severity(rule, model):
    return "warning" if rule in LINT and rule not in getattr(model, "strict", ()) else "error"


def violations(model, only=None):
    """Every problem as (rule, "path: message", severity), checks in order; the checks run only once every reference
    resolves, since they read the model through them."""
    rows = model.parse_problems or [row for name, _, check in RULES if not only or name in only for row in tagged(name, check(model))]
    rows = tagged("form", rows)
    return [(rule, text, severity(rule, model)) for rule, text in rows]


def tagged(name, problems):
    return [problem if isinstance(problem, tuple) else (name, problem) for problem in problems]


def line(rule, text):
    """`path: rule: message`, the path being what the problem's sentence opens with."""
    where, _, message = text.partition(": ")
    # a sentence that opens with no path, or with words before its first colon, is about the whole document
    return f"{where}: {rule}: {message}" if message and not re.search(r"\s", where) else f"schema: {rule}: {text}"

"""Schema checks: each takes a Model and returns the problems it found, each a sentence that says what to fix, or a
(rule, sentence) pair when it states a narrower rule than the check's own."""
import re

from . import formula
from . import plan as params
from . import prover
from . import sources as source_files
from .model import MEMBER, places, plan, split_top, walk_steps

NODE_MEDIA, EDGE_MEDIA = {"tree", "checklist"}, {"diff", "payload"}
first_word = lambda t: t.strip().split()[0].lower() if t and t.strip() else ""
plain_verb = lambda w: not ((w.endswith("ed") and not w.endswith("eed")) or w.endswith("ing") or (w.endswith("s") and not w.endswith("ss")))


def form(model):
    """The file read as a model: every reference points at something (model.parse), and the plan holds together."""
    return model.parse_problems + params.problems(model.m, [r[0] for r in RULES])


def steps(model):
    out = []
    for s in model.m["scenarios"]:
        for k, st in enumerate(walk_steps(s["walk"])):
            if not (isinstance(st, dict) and str(st.get("does", "")).strip() and str(st.get("expects", "")).strip()):
                out.append(f'{s["slug"]}: step {k + 1} says what it does and what it expects ({{"place", "does", "expects"}})')
            elif len(places(st)) > 1 and not all(model.kind_of.get(x) == "topology" and model.node_level.get(x) == model.node_level.get(places(st)[0]) for x in places(st)):
                out.append(f'{s["slug"]}: step {k + 1} is at several nodes, so they are parts of one component level')
        out += model.walks[s["slug"]][1]
    return out


def scoped(model):
    out = []
    for slug, h in model.home.items():
        sc = next(s for s in model.m["scenarios"] if s["slug"] == slug)
        climb = [x for x in plan(sc["walk"])[0] if x in model.nodes and h not in model.ancestors(model.node_level[x])]
        if climb:
            out.append(f'{slug}: starts in {h} but climbs above it at {climb[0]}')
    # every level needs Scenarios of its own, or (plan scenarios: entry) only the root and levels things enter from outside
    own = [level for level in model.m["levels"] if model.plan["scenarios"] == "every" or not level.get("parent") or level.get("triggers")]
    out += [f'{level["id"]}: give this level a Scenario of its own' for level in own if level["id"] not in model.home.values()]
    return out


def coverage(model):
    used = set().union(*model.footprint.values()) if model.footprint else set()
    orphans = sorted(model.elements() - used)
    return [f"no Scenario uses {k} {x}; drop it or name the use it serves" for k, x in orphans]


def basis(model):
    out = []
    for s, f in model.footprint.items():
        subs = [t for t, g in model.footprint.items() if t != s and g <= f and model.home.get(t) == model.home.get(s)]
        if subs and set().union(*(model.footprint[t] for t in subs)) == f:
            out.append(f"{s} is the union of {subs}; drop it")
    return out


def placement(model):
    out = []
    event_ops = {x for level in model.m["levels"] if level["kind"] == "state" for e in level["edges"] + level.get("triggers", []) for x in e.get("ops", [])}
    edge_ops = {x for _, e in list(model.edges.values()) + list(model.trigs.values()) for x in e.get("ops", [])}
    sits = model.sits()
    for o in model.ops:
        if o not in sits:
            out.append(f"{o}: place it on a node or an event")
        elif o in edge_ops - event_ops:
            out.append(f"{o}: only an event edge carries an operation")
    out += [f"{i}: place it on a node or an edge" for i in model.rules if i not in sits]
    return out


def explained(model):
    out = []
    for k, (level, e) in model.edges.items():
        if not (e.get("what") or e.get("ops") or e.get("rules") or model.is_abstract(level, e["to"])):
            out.append(f'{level["id"]}: {e["from"]}>{e["to"]} says nothing; give it a sentence, an operation or a guard')
    for k, (level, t) in model.trigs.items():
        if not (t.get("what") or t.get("ops") or t.get("rules")):
            out.append(f'{level["id"]}: trigger {t["label"]} says nothing')
    return out


def mechanism(model):
    out = []
    walks = lambda tr: any(model.kind_of.get(x) in ("workflow", "state") for x in tr)
    if not any(level["kind"] in ("workflow", "state") for level in model.m["levels"]):
        return out   # nothing runs: a body of knowledge is claims and what they rest on
    rooted = [s for s in model.m["scenarios"] if model.home.get(s["slug"]) == model.root]
    out += [f'{s["slug"]}: a root Scenario walks no activity or state' for s in rooted if not walks(plan(s["walk"])[0])]
    parts = [x for x, k in model.kind_of.items() if k == "topology"]
    if not parts:
        out.append("no component level: show what the system is made of")
    out += [f"{x}: in no root Scenario that also walks an activity or state" for x in parts
            if not any(x in plan(s["walk"])[0] and walks(plan(s["walk"])[0]) for s in rooted)]
    return out


def partitions(model):
    out = []
    for level in model.m["levels"]:
        partition_ids = {p["id"] for p in level.get("partitions", [])}
        if not partition_ids:
            continue
        if len(partition_ids) < 2:
            out.append(f'{level["id"]}: one partition says nothing; drop it')
        out += [f'{level["id"]}: put {n["id"]} in a partition' for n in level["nodes"] if n.get("partition") not in partition_ids]
        side = {n["id"]: n.get("partition") for n in level["nodes"]}
        if level["kind"] == "state":   # its partitions are orthogonal regions (Harel), which four-states checks
            continue
        for e in level["edges"]:
            contract = e.get("rules") or e.get("ops") or any(x.get("type") == "payload" for x in e.get("media", []))
            if level["kind"] != "topology" and side.get(e["from"]) != side.get(e["to"]) and not contract:
                out.append(f'{level["id"]}: {e["from"]}>{e["to"]} crosses partitions; give it a payload, guard or operation')
    return out



def four_states(model):
    """Each region of a state level holds every subject instance in exactly one state (Koppel's four states:
    https://note89.github.io/state-of-emergency/): one initial state, events that stay in the region, every state
    reached, and no two states alike."""
    out = []
    for level in model.m["levels"]:
        if level["kind"] != "state":
            continue
        lid, side = level["id"], {n["id"]: n.get("partition") or "the level" for n in level["nodes"]}
        inits = [level["initial"]] if isinstance(level.get("initial"), str) else level.get("initial") or []
        for r in sorted(set(side.values())):
            k = sum(1 for i in inits if side.get(i) == r)
            if k == 0:
                out.append(("region-without-initial", f"{lid}: Missing: an instance starts in no state of {r}; name one initial state there"))
            elif k > 1:
                out.append(f"{lid}: Overloaded: an instance starts in {k} states of {r} at once; keep one initial state")
        out += [f'{lid}: Missing: event {e["label"]} leaves its region, so the instance is in no state of {side[e["from"]]}; regions meet only through syncs'
                for e in level["edges"] if side.get(e["from"]) != side.get(e["to"])]
        seen, todo = set(), list(inits) + [t["to"] for t in level.get("triggers", [])]
        while todo:
            x = todo.pop()
            if x not in seen:
                seen.add(x)
                todo += [e["to"] for e in level["edges"] if e["from"] == x]
        # a region with no initial state is one fault, already reported, not one per state it leaves unreached
        started = {side.get(i) for i in inits}
        out += [f'{lid}: Illegal: no event reaches {n["id"]}; add the event that enters it, or drop it' for n in level["nodes"]
                if n["id"] not in seen and side[n["id"]] in started]
        def alike(n):
            end = lambda x: "itself" if x == n["id"] else x
            return (side[n["id"]], frozenset((e["label"], end(e["to"])) for e in level["edges"] if e["from"] == n["id"]),
                    frozenset((e["label"], end(e["from"])) for e in level["edges"] if e["to"] == n["id"]),
                    frozenset(n.get("ops") or []), frozenset(n.get("rules") or []), n["id"] in inits)
        groups = {}
        for n in level["nodes"]:
            groups.setdefault(alike(n), []).append(n["id"])
        out += [f'{lid}: Redundant: no event or rule tells {" and ".join(g)} apart; merge them or give each its own' for g in groups.values() if len(g) > 1]
    return out

GATES = {"checking", "reviewing", "validating", "verifying", "testing", "judging", "approving", "gating", "evaluating"}


def quantities(model):
    """Quantities add up: a count is what enters and what leaves it, a node that holds nothing passes on what it
    receives, a flow into or out of a stock is in the stock's unit, and a deadline says what happens when it passes."""
    out, same = [], lambda a, b: abs(a - b) <= 1e-9 * max(1, abs(a), abs(b))
    for level in model.m["levels"]:
        for e in level["edges"]:
            q = e.get("qty")
            if q and q["kind"] not in ("flow", "count", "delay"):
                out.append(f'{level["id"]}: {e["label"]} carries a flow, a count or a delay, not a {q["kind"]}')
            if q and q["kind"] == "delay" and not any(x is not e and x["from"] == e["from"] and "failure" in x.get("mark", []) for x in level["edges"]):
                out.append(f'{level["id"]}: {e["label"]} has a deadline; draw what happens when it passes, an edge from {e["from"]} marked failure')
        for n in level["nodes"]:
            q = n.get("qty")
            if q and q["kind"] not in ("stock", "count", "capacity"):
                out.append(f'{level["id"]}: {n["label"]} holds a stock, a count or a capacity, not a {q["kind"]}')
                continue
            sides = {"in": [e for e in level["edges"] if e["to"] == n["id"] != e["from"]],
                     "out": [e for e in level["edges"] if e["from"] == n["id"] != e["to"]]}
            if q and q["kind"] == "stock":
                out += [f'{level["id"]}: {e["label"]} moves {e["qty"]["unit"]}, not the {q["unit"]} that {n["label"]} holds'
                        for es in sides.values() for e in es
                        if e.get("qty", {}).get("kind") == "flow" and "unit" in e["qty"] and "unit" in q
                        and e["qty"]["unit"].split("/")[0].strip() != q["unit"]]
                continue
            told = {k: [e["qty"] for e in es if e.get("qty", {}).get("kind") in ("flow", "count")] for k, es in sides.items()}
            full = {k: v for k, v in told.items() if v and len(v) == len(sides[k]) and len({x.get("unit", "") for x in v}) == 1}
            total = {k: sum(x["value"] for x in v) for k, v in full.items()}
            if q and q["kind"] == "count":
                out += [f'{level["id"]}: {n["label"]} counts {q["value"]}, but {total[k]} {"enter" if k == "in" else "leave"}'
                        for k in total if not same(total[k], q["value"])]
            elif len(total) == 2 and full["in"][0].get("unit", "") == full["out"][0].get("unit", "") and not same(total["in"], total["out"]):
                out.append(f'{level["id"]}: {n["label"]} holds nothing, yet {total["in"]} enter and {total["out"]} leave')
    return out


def paths(model):
    """A workflow or state level shows its main path, and every gate shows how it fails."""
    out = []
    for level in model.m["levels"]:
        if level["kind"] == "topology":
            continue
        if not any("happy" in e.get("mark", []) for e in level["edges"]):
            out.append(f'{level["id"]}: mark the main path happy')
        parent = level.get("parent") and model.level_of(level["parent"])
        port_fail = {fr for f in level.get("out", []) for fr in ([f["from"]] if isinstance(f.get("from"), str) else f.get("from", []))
                     if parent and any(e["label"] == f.get("edge") and "failure" in e.get("mark", []) for e in parent["edges"])}
        for n in level["nodes"]:
            if first_word(n["label"]) in GATES:
                fails = any(e["from"] == n["id"] and "failure" in e.get("mark", []) for e in level["edges"]) or n["id"] in port_fail
                if not fails:
                    out.append(f'{level["id"]}: {n["label"]} is a gate; draw how it fails (a failure edge or port)')
    return out


def syncs(model):
    """Regions meet only through syncs (Meng and Jackson): when an event in one region, where a state holds, then an event in another."""
    out = []
    for level in model.m["levels"]:
        region = {n["id"]: n.get("partition") for n in level["nodes"]}
        events = {e["label"]: region.get(e["from"]) for e in level["edges"]}
        for y in level.get("syncs", []):
            name = y.get("name", "?")
            if level["kind"] != "state" or not level.get("partitions"):
                out.append(f'{level["id"]}: sync {name} joins regions, so it sits on a state level with partitions')
            elif events[y["when"]] == events[y["then"]]:
                out.append(f'{level["id"]}: sync {name} joins two events of one region; join regions')
            if not y.get("what"):
                out.append(f'{level["id"]}: sync {name} says nothing; give it a sentence')
    return out


def naming(model):
    out = []
    for level in model.m["levels"]:
        k = level["kind"]
        for n in level["nodes"]:
            if k == "workflow" and not first_word(n["label"]).endswith("ing"):
                out.append(f'{level["id"]}: activity "{n["label"]}" starts with a verb in -ing')
            if n.get("abstract") and k != "topology":
                out.append(f'{level["id"]}: only a component can be abstract')
        for e in level["edges"]:
            w = first_word(e.get("label", ""))
            if k == "topology" and not w.endswith("s"):
                out.append(f'{level["id"]}: relation "{e["label"]}" starts with a present-tense verb (uses, opens)')
            if k == "state" and not plain_verb(w):
                out.append(f'{level["id"]}: event "{e["label"]}" starts with a plain verb (merge, mark ready)')
            if k == "workflow" and w.endswith("ing") and not e.get("is"):
                out.append(f'{level["id"]}: artifact "{e["label"]}" is a noun phrase')
            if model.is_abstract(level, e["from"]) and not model.is_abstract(level, e["to"]):
                out.append(f'{level["id"]}: abstract {e["from"]} cannot depend on concrete {e["to"]}')
        for t in level.get("triggers", []):
            w = first_word(t.get("label", ""))
            if (k == "state" and not plain_verb(w)) or (k == "workflow" and w.endswith("ing")):
                out.append(f'{level["id"]}: trigger "{t["label"]}" is named like the level\'s edges')
        for x in level["nodes"] + level["edges"] + level.get("triggers", []):
            if {"happy", "failure"} <= set(x.get("mark", [])):
                out.append(f'{level["id"]}: {x.get("label")} is marked both happy and failure')
    return out


def media(model):
    out = []
    words = lambda z: set(re.findall(r"\w{2,}", z))
    for level in model.m["levels"]:
        hosts = [(n, "node") for n in level["nodes"]] + [(e, "edge") for e in level["edges"]] + [(level, "level")]
        insights = 0
        for x, where in hosts:
            for md in x.get("media", []):
                t = md.get("type")
                if (t in NODE_MEDIA and where == "edge") or (t in EDGE_MEDIA and where == "node"):
                    out.append(f'{level["id"]}: {t} does not sit on a {where}')
                if t != "insight":
                    continue
                insights += 1
                here = set(model.ops) | set(model.rules) if where == "level" else set(x.get("ops", [])) | set(x.get("rules", []))
                miss = [f for f in ("move", "vs", "gain", "rule") if not str(md.get(f, "")).strip()]
                mv, desc = words(md.get("move", "")), words(x.get("what", x.get("why", "")))
                if miss:
                    out.append(f'{level["id"]}: an insight needs move, vs, gain and rule (missing {miss})')
                elif md["rule"] not in here:
                    out.append(f'{level["id"]}: the insight\'s rule {md["rule"]} must sit on the same node or edge')
                elif mv and len(mv & desc) / len(mv) > 0.5:
                    out.append(f'{level["id"]}: an insight names what is distinctive, not what the description says')
        if insights > 1:
            out.append(f'{level["id"]}: {insights} insights; keep the most distinctive one')
    return out


def unique_names(model):
    m = model.m
    norm = lambda t: re.sub(r"[\s_-]+", " ", t.strip().lower())
    linked = {(level["id"], e["label"]) for level in m["levels"] for e in level["edges"] if e.get("is")}
    names = ([("scenario", s["slug"]) for s in m["scenarios"]] + [("operation", o["slug"]) for o in m["operations"]]
             + [("rule", i["slug"]) for i in m["rules"]] + [("level", level["title"]) for level in m["levels"]]
             + [("node", n["label"]) for n in model.nodes.values()]
             + [("partition", lab) for lab in {p["label"] for level in m["levels"] for p in level.get("partitions", [])}]   # one owner may recur across levels
             + [("edge", lab) for lab in {e["label"] for level in m["levels"] for e in level["edges"]   # a verb may recur
                                          if e.get("label") and not model.is_abstract(level, e["to"]) and (level["id"], e["label"]) not in linked}]
             + [("trigger", t["label"]) for level in m["levels"] for t in level.get("triggers", [])]
             + [("sync", y["name"]) for level in m["levels"] for y in level.get("syncs", []) if y.get("name")])
    seen, out = {}, []
    for kind, name in names:
        seen.setdefault(norm(name), []).append(f"{kind} '{name}'")
    out += [" = ".join(v) + "; rename one" for v in seen.values() if len(v) > 1]
    for level in m["levels"]:
        for e in level["edges"]:
            tgt = model.nodes.get(e.get("is"))
            if e.get("is") and not (level["kind"] == "workflow" and tgt and model.kind_of[e["is"]] == "topology" and prover.singular(prover.ident(tgt["label"])) == prover.singular(prover.ident(e["label"]))):
                out.append(f'{level["id"]}: {e["from"]}>{e["to"]} "is" names a component with the same label')
    return out


def typed(model):
    """Types are exact names the module declares; signatures, attributes and relations agree with the drawing."""
    world = prover.World(model)
    out = list(world.problems)
    for t, txt in (model.m.get("types") or {}).items():
        if not re.sub(r"^\s*\{[^}]*\}", "", str(txt)).strip():
            out.append(f"type {t}: say in a sentence what it is")
    for o in model.m["operations"]:
        sl = o["slug"]
        if sl not in model.sigs:
            out.append(f'{sl}{o.get("sig", "")}: write Receiver.verb and (name: Type, …) → Result')
            continue
        params = split_top(re.match(r"\s*\((.*)\)", o["sig"]).group(1))
        out += [f"{sl}: parameter {p} needs name: Type" for p in params if not re.fullmatch(rf"{MEMBER}\s*:\s*.+", p)]
    for level in model.m["levels"]:
        for n in level["nodes"]:
            ops = [x for x in n.get("ops", []) if x in model.sigs]
            if level["kind"] == "topology":
                out += [f'{level["id"]}: {x} sits on {n["label"]}, so its receiver is {prover.ident(n["label"])}' for x in ops if model.sigs[x][0] != prover.ident(n["label"])]
            if level["kind"] == "workflow" and ops:
                outs = [e["label"] for e in level["edges"] if e["from"] == n["id"]]
                made = {r for x in ops for r in prover.Type(re.search(r"→\s*(.+)$", model.ops[x]["sig"]).group(1)).refs()}
                if outs and not any(made & prover.artifact_types(l) for l in outs):
                    out.append(f'{level["id"]}: {n["label"]} hands on {", ".join(outs)}, but none of its operations returns it')
            for a in n.get("attrs", []):
                ma = re.fullmatch(rf"({MEMBER})\s*:\s*(.+)", a)
                if not ma or level["kind"] != "topology":
                    out.append(f'{n["label"]}: attribute "{a}" is name: Type on a component')
        if level["kind"] != "topology":
            continue
        comp = {prover.ident(n["label"]): n for n in level["nodes"]}
        attrs = {n["id"]: [(nm, t) for _, nn, nm, t in world._attrs() if nn is n] for n in level["nodes"]}
        for n in level["nodes"]:
            for nm, t in attrs[n["id"]]:
                peers = [comp[r] for r in t.names if len(t.names) == 1 and not t.tuple and r in comp and comp[r] is not n and not comp[r].get("abstract")]
                for p in peers:
                    if not any(e["from"] == n["id"] and e["to"] == p["id"] for e in level["edges"]):
                        out.append(f'{n["label"]}.{nm} points at {p["label"]}; draw the relation')
        for e in level["edges"]:
            if model.is_abstract(level, e["to"]):
                continue
            to = prover.ident(model.nodes[e["to"]]["label"])
            cands = [nm for nm, t in attrs[e["from"]] if to in t.refs()]
            if e.get("attr"):
                if e["attr"] not in cands:
                    out.append(f'{level["id"]}: relation {e["label"]} names attribute {e["attr"]}, which does not point at {model.nodes[e["to"]]["label"]}')
            elif len(cands) > 1:
                out.append(f'{level["id"]}: relation {e["label"]} could be {cands}; name one with attr')
    return out


def alloy_names(model):
    """Every name the module declares is an Alloy name (ASCII, starting with a letter) clear of Alloy's keywords
    and the translation's own words; caught here, before the slow Alloy run."""
    m, found = model.m, []
    for level in m["levels"]:
        found += [(prover.ident(n["label"]), n["label"]) for n in level["nodes"]]
        found += [(prover.lower(x["label"]), x["label"]) for x in level["edges"] + level.get("triggers", []) if level["kind"] == "state" and x.get("label")]
        found += [((prover.ident if a.split(":", 1)[-1].strip() == "Bool" else str)(a.split(":")[0].strip()), a) for n in level["nodes"] for a in n.get("attrs", [])]
        found += [(prover.lower(e["label"]), e["label"]) for e in level["edges"] if level["kind"] in ("topology", "workflow") and e.get("label")]
        if level["kind"] == "workflow":
            found.append((prover.ident(level["title"]), level["title"]))
    for o in m["operations"]:
        if o["slug"] in model.sigs:
            found.append((model.sigs[o["slug"]][2], o["slug"]))
            found += [(p, o["slug"]) for p in model.sigs[o["slug"]][1]]
    found += [(prover.lower(i["slug"]), i["slug"]) for i in m["rules"]]
    found += [(t, t) for t in (m.get("types") or {})]
    for t in [x for level in m["levels"] for n in level["nodes"] for x in n.get("attrs", [])] + [o.get("sig", "") for o in m["operations"]] + list((m.get("types") or {}).values()):
        for lit in re.findall(r"\{([^}]*)\}", str(t)):
            found += [(v.strip(), lit) for v in lit.split(",")]
    out = {f'"{n}" in {where} is a word Alloy or the translation reserves; rename it' for n, where in found if n in formula.RESERVED}
    out |= {f'{where} gives no Alloy name ("{n}"); write it in ASCII letters' for n, where in found if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", str(n))}
    return sorted(out)


def vocabulary(model):
    """Formulas are Alloy over the module's names, with every variable bound and no name hidden; every name is an
    Alloy name (alloy_names)."""
    world, out = prover.World(model), alloy_names(model)
    for i in model.m["rules"]:
        out += world.check_formula(i["formula"], i["slug"])
    for sl, op in list(world.change.items()) + list(world.query.items()):
        extra = ["self"] + [p for p, _, _ in op["params"]] + (["result"] if op["rdecl"] else [])
        for part in ("pre", "post"):
            if op.get(part):
                out += world.check_formula(op[part], f"{sl} {part}", extra)
    for level in model.m["levels"]:
        if level.get("init"):
            out += world.check_formula(level["init"], f'{level["id"]} init')
    return out


def opens(model):
    """Zoom as refinement: an unmarked same-kind open keeps its node's interface, every edge into or out of the node
    a port of the child (a state child takes them at its initial state); a kind change is a view link, marked view;
    a same-kind open with no interface claim is marked nest, and warned."""
    out = []
    for level in model.m["levels"]:
        n = level.get("parent") and model.nodes[level["parent"]]
        if not n:
            continue
        parent_level, link = model.level_of(n["id"]), n.get("link")
        if parent_level["kind"] != level["kind"]:
            out += [] if link == "view" else [("view-link-unmarked", f'{n["id"]}: opens a {level["kind"]} level from a {parent_level["kind"]} level; mark it link: view')]
        elif link == "view":
            out.append(("form", f'{n["id"]}: a view link changes kind; a same-kind open is unmarked or nest'))
        elif link == "nest":
            out.append(("nest-unrefined", f'{n["id"]}: nests a {level["kind"]} level with no interface claim; map its edges onto ports to refine it'))
        elif level["kind"] != "state":
            ids = {x["id"] for x in level["nodes"]}
            # lists, not sets: two parent edges may share a label, and each needs its own port
            need_in = sorted([e["label"] for e in parent_level["edges"] if e["to"] == n["id"]] + [t["label"] for t in parent_level.get("triggers", []) if t["to"] == n["id"]])
            need_out = sorted([e["label"] for e in parent_level["edges"] if e["from"] == n["id"]])
            got_in = sorted(f.get("edge") for f in level.get("in", []) if f.get("to") in ids)
            got_out = sorted(f.get("edge") for f in level.get("out", []) if f.get("from") and set([f["from"]] if isinstance(f["from"], str) else f["from"]) <= ids)
            if (got_in, got_out) != (need_in, need_out):
                out.append(("opens-interface", f'{level["id"]}: in {got_in} should be {need_in}; out {got_out} should be {need_out}'))
    return out


def gates(model):
    """A workflow forks into branches that run side by side and joins them again: a fork has two or more edges out, a
    join two or more in, and every join has a fork before it on its level."""
    out = []
    for level in model.m["levels"]:
        for n in level["nodes"]:
            g = n.get("gate")
            if g and level["kind"] != "workflow":
                out.append(("form", f'{n["id"]}: only a workflow step is a {g}'))
                continue
            ins = [e["from"] for e in level["edges"] if e["to"] == n["id"]]
            outs = [e["to"] for e in level["edges"] if e["from"] == n["id"]]
            if g == "fork" and len(outs) < 2:
                out.append(("gates", f'{n["id"]}: a fork has two or more edges out'))
            if g == "join":
                def above(x):
                    seen, todo = set(), [x]
                    while todo:
                        y = todo.pop()
                        if y not in seen:
                            seen.add(y)
                            todo += [e["from"] for e in level["edges"] if e["to"] == y]
                    return {y for y in seen if model.nodes[y].get("gate") == "fork"}
                # one fork must lie above every edge in, so each comes from one of its branches
                if len(ins) < 2 or not set.intersection(*map(above, ins)):
                    out.append(("join-without-fork", f'{n["id"]}: a join has two or more edges in, from branches of a fork before it'))
    return out


def sources(model):
    out, model.sources_status = source_files.problems(model.m)
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
CHECKS = {r[0] for r in RULES}


def unknown(only, known):
    """The refusal for a check name nobody runs, naming the known ones; None when every name is known."""
    bad = [x for x in only or [] if x not in known and x != "form"]
    return f"unknown check {', '.join(bad)}; known: {', '.join(sorted(known | {'form'}))}" if bad else None


def severity(rule, model):
    return "warning" if rule in LINT and rule not in getattr(model, "strict", ()) else "error"


def violations(model, only=None):
    """Every problem as (rule, "path: message", severity), checks in order; the checks run only once every reference
    resolves, since they read the model through them."""
    rows = model.parse_problems or [x for name, _, fn in RULES if not only or name in only for x in tagged(name, fn(model))]
    rows = tagged("form", rows)
    return [(rule, text, severity(rule, model)) for rule, text in rows]


def tagged(name, problems):
    return [p if isinstance(p, tuple) else (name, p) for p in problems]


def line(rule, text):
    """`path: rule: message`, the path being what the problem's sentence opens with."""
    where, _, message = text.partition(": ")
    # a sentence that opens with no path, or with words before its first colon, is about the whole document
    return f"{where}: {rule}: {message}" if message and not re.search(r"\s", where) else f"schema: {rule}: {text}"

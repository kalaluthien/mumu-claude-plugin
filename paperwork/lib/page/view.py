"""A zoom diagram's view of a system model: the view file (layout, views, depth, language, screens), how it joins
the system file into the model the page reads, and the checks of the drawing."""
import copy
import json
import pathlib
import re
import unicodedata

from schema import plan as system_plan
from schema.model import Model, levels_of, shape, walk_steps

ASSETS = pathlib.Path(__file__).resolve().parents[2] / "skills/zoom/references/ui/html/assets"
SCHEMA = json.loads((ASSETS / "view-schema.json").read_text(encoding="utf-8"))
LIMITS = json.loads((ASSETS / "phone-limits.json").read_text(encoding="utf-8"))   # a phone's limits, shared with the engine

DEFAULTS = {
    "views": ([], "list", "the diagrams a practitioner of this domain expects, each drawn by a level or left out with why"),
    "depth": ("working", ("overview", "working", "detailed"), "overview features the root and one level in its views; detailed makes every operation one action; the page keeps every level"),
    "deep": ([], "node ids", "nodes opened even where the depth rules would stop"),
    "shallow": ([], "node ids", "nodes left closed on purpose; the page marks them"),
    "strict": ([], "check names", "style checks of the drawing that block instead of warning"),
    "max_nodes": (7, "number", "most nodes on one level"),
    "show": ({"formulas": True, "replay": True, "media": True}, "flags", "what the page shows"),
    "why": ({}, "parameter: sentence", "why each changed default was changed"),
}
PAGE_ORDER = ("intent", "views", "depth", "deep", "shallow", "scenarios", "prove", "strict", "max_nodes", "show", "why")
TOP, PLAN_KEYS, NODE_KEYS, EDGE_KEYS = ("lang", "next", "screens"), ("views", "depth", "deep", "shallow", "show", "max_nodes"), ("x", "y", "ui"), ("via",)


def edge_key(level, edge):
    """An edge's key within its level: from>to, and #label when two edges join the same pair."""
    twins = sum(1 for other in level["edges"] if (other["from"], other["to"]) == (edge["from"], edge["to"]))
    return f'{edge["from"]}>{edge["to"]}' + (f'#{edge["label"]}' if twins > 1 else "")


def levels(data):
    """(level id, level) for every level: root, or the id of the node that opens it."""
    return [(opener or "root", level) for level, opener in levels_of(data)]


def split(merged):
    """A whole model as (system, view): the view takes the drawing's keys, the system keeps the rest."""
    system, view = copy.deepcopy(merged), {}
    for k in TOP:
        if k in system:
            view[k] = system.pop(k)
    plan, view_plan = system.get("plan", {}), {}
    for k in PLAN_KEYS:
        if k in plan:
            view_plan[k] = plan.pop(k)
    if "strict" in plan:
        view_strict = [check_name for check_name in plan["strict"] if check_name in CHECKS]
        plan["strict"] = [check_name for check_name in plan["strict"] if check_name not in CHECKS]
        view_plan.update({"strict": view_strict} if view_strict else {})
        if not plan["strict"]:
            del plan["strict"]
    if "why" in plan:
        view_why = {k: plan["why"].pop(k) for k in list(plan["why"]) if k in PLAN_KEYS or (k == "strict" and "strict" in view_plan and "strict" not in plan)}
        view_plan.update({"why": view_why} if view_why else {})
        if not plan["why"]:
            del plan["why"]
    if view_plan:
        view["plan"] = view_plan
    out = {}
    for level_id, level in levels(system):
        nodes = {node["id"]: {k: node.pop(k) for k in NODE_KEYS if k in node} for node in level.get("nodes", [])}
        edges = {}
        for edge in level.get("edges", []):
            edge_view = {k: edge.pop(k) for k in EDGE_KEYS if k in edge}
            if edge_view:
                edges[edge_key(level, edge)] = edge_view
        entry = ({"nodes": {node_id: node_view for node_id, node_view in nodes.items() if node_view}} if any(nodes.values()) else {}) | ({"edges": edges} if edges else {})
        if entry:
            out[level_id] = entry
    if out:
        view["levels"] = out
    return system, view


def merge(system, view):
    """The whole model the page reads: the system's keys in its order, `next` and `lang` after `title`, `screens`
    before `level`; a node's x and y after its label and ui last; an edge's via last."""
    out = {}
    for k, value in system.items():
        if k == "level" and "screens" in view:
            out["screens"] = view["screens"]
        out[k] = copy.deepcopy(value)
        if k == "title":
            out.update({name: view[name] for name in ("next", "lang") if name in view})
    if "plan" in view:
        plan, view_plan = out.setdefault("plan", {}), view["plan"]
        why, strict = {**plan.get("why", {}), **view_plan.get("why", {})}, plan.get("strict", []) + view_plan.get("strict", [])
        plan.update({k: setting for k, setting in view_plan.items() if k not in ("why", "strict")})
        if strict:
            plan["strict"] = strict
        if why:
            plan.pop("why", None)
            plan["why"] = why
    given = view.get("levels", {})
    for level_id, level in levels(out):
        entry = given.get(level_id, {})
        if "nodes" in level:
            nodes = []
            for node in level["nodes"]:
                node_view, keys = entry.get("nodes", {}).get(node["id"], {}), list(node)
                head = keys[:keys.index("label") + 1] if "label" in keys else keys[:1]
                new = {k: node[k] for k in head} | {k: node_view[k] for k in ("x", "y") if k in node_view}
                new |= {k: node[k] for k in keys if k not in new}
                nodes.append(new | ({"ui": node_view["ui"]} if "ui" in node_view else {}))
            level["nodes"] = nodes
        for edge in level.get("edges", []):
            edge.update(entry.get("edges", {}).get(edge_key(level, edge), {}))
    return out


def page_plan(merged):
    """The plan the page reads, in the order it has always had: system and view defaults with the model's plan."""
    defaults = {k: entry[0] for k, entry in system_plan.DEFAULTS.items()} | {k: entry[0] for k, entry in DEFAULTS.items()}
    plan = {k: copy.deepcopy(defaults[k]) for k in PAGE_ORDER}
    plan.update({k: setting for k, setting in (merged.get("plan") or {}).items() if k not in system_plan.LOCAL})
    if isinstance(plan["show"], dict):
        plan["show"] = {**DEFAULTS["show"][0], **plan["show"]}
    return plan


def attach(system, view):
    """Where the view names something the system lacks: a level, node, edge or screen block."""
    out, by = [], dict(levels(system))
    screens = view.get("screens") or {}
    for level_id, entry in (view.get("levels") or {}).items():
        level = by.get(level_id)
        if level is None:
            out.append(f"view: levels.{level_id} is no level (root, or a node that opens one)")
            continue
        ids, keys = {node["id"] for node in level.get("nodes", [])}, {edge_key(level, edge) for edge in level.get("edges", [])}
        out += [f"view: levels.{level_id}.nodes.{node_id} is no node of that level" for node_id in entry.get("nodes", {}) if node_id not in ids]
        out += [f"view: levels.{level_id}.edges.{k} is no edge of that level (from>to, #label for twins)" for k in entry.get("edges", {}) if k not in keys]
        for node_id, node_view in entry.get("nodes", {}).items():
            screen_pointer = node_view.get("ui")
            if screen_pointer and not (screen_pointer["screen"] in screens and screen_pointer["block"] in {block["id"] for block in screens[screen_pointer["screen"]]["blocks"]}):
                out.append(f"{node_id}: ui points at no screen block")
    return out


def plan_problems(system, view):
    """What the schemas cannot say about the view's plan: every expected view is drawn or explained, deep nodes open
    a level, shallow ones do not, strict names drawing checks, every changed default says why, and `next` says what
    the reader does after."""
    out, given = [], view.get("plan") or {}
    opens = {level_id for level_id, _ in levels(system)} - {"root"}
    nodes = {node["id"] for _, level in levels(system) for node in level.get("nodes", [])}
    if not given.get("views"):
        out.append("plan: list the views a practitioner of this domain expects (views)")
    for view_entry in given.get("views") or []:
        if ("level" in view_entry) == ("why" in view_entry):
            out.append(f'plan: view {view_entry.get("name")} is drawn by a level or left out with why, one of the two')
        elif "level" in view_entry and view_entry["level"] != "root" and view_entry["level"] not in opens:
            out.append(f'plan: view {view_entry.get("name")} names no level {view_entry["level"]}')
    out += [f"plan: {node_id} is no node" for node_id in given.get("deep", []) + given.get("shallow", []) if node_id not in nodes]
    out += [f"plan: deep {node_id} opens no level" for node_id in given.get("deep", []) if node_id in nodes and node_id not in opens]
    out += [f"plan: {node_id} is shallow, so it opens no level" for node_id in given.get("shallow", []) if node_id in opens]
    out += [f"plan: strict {check_name} is no drawing check" for check_name in given.get("strict", []) if check_name not in CHECKS]
    changed = [k for k in given if k not in ("views", "why") and given[k] != DEFAULTS[k][0]]
    out += [f"plan: say why {k} changed (in why)" for k in changed if k not in (given.get("why") or {})]
    if not view.get("next", "").strip():
        out.append("`next` is empty: write the reader's next action or choice in one sentence")
    return out


def size(system_model):
    out = []
    for level in system_model.document["levels"]:
        n = len(level["nodes"])
        if n > system_model.plan["max_nodes"]:
            out.append(f'{level["id"]}: {n} nodes; group those that work alike and open them below')
        if level.get("parent") and n < 2:
            out.append(f'{level["id"]}: opens with {n} node; merge it into {level["parent"]}')
    return out


def phone(system_model):
    """A phone's root is laid out again in two columns or one, so the author's columns never decide whether it fits.
    Partitions then stack as bands of rows, and two rows of two cells join by at most three lines that do not cross
    (two straight down, one across); more links between two partitions detour round the sides and meet. Limits in
    assets/phone-limits.json, shared with the engine; render measures the fit itself."""
    out = []
    for level in system_model.document["levels"]:
        if level.get("parent") or not level.get("partitions"):
            continue
        part = {node["id"]: node.get("partition") for node in level["nodes"]}
        links = {}
        for edge in level["edges"]:
            first_partition, second_partition = part.get(edge["from"]), part.get(edge["to"])
            if first_partition != second_partition and first_partition and second_partition:   # a node outside every partition is the partitions check's to report
                links.setdefault(tuple(sorted((first_partition, second_partition))), set()).add(frozenset((edge["from"], edge["to"])))
        for (first_partition, second_partition), pairs in sorted(links.items()):
            if len(pairs) > LIMITS["partitionLinks"]:
                out.append(f'{level["id"]}: partitions {first_partition} and {second_partition} are joined at {len(pairs)} pairs of nodes, more than the '
                           f'{LIMITS["partitionLinks"]} a phone can draw apart; route some through one node or open them in a level below')
    return out


def depth(system_model):
    """Depth picks which levels the views feature; the page keeps every level the model holds."""
    if system_model.plan["depth"] != "overview":
        return []
    return [f'view {view.get("name")}: an overview features the root and one level, and {view["level"]} lies {system_model.depth(view["level"])} below'
            for view in system_model.plan.get("views") or [] if view.get("level") in system_model.levels and system_model.depth(view["level"]) > 1]


def names(system_model):
    """Every term is English whatever the reader's language; only descriptions follow it."""
    data = system_model.document
    terms = [data.get("title", "")] + [term for level in data["levels"] for term in [level.get("title", "")]
             + [element.get("label", "") for element in level["nodes"] + level["edges"] + level.get("triggers", []) + level.get("partitions", []) + level.get("regions", [])]]
    for medium in [media_item for level in data["levels"] for owner in [level] + level["nodes"] + level["edges"] for media_item in owner.get("media", [])]:
        terms.append(medium.get("title", ""))
        if medium.get("type") == "facts":
            terms += [fact[0] for fact in medium.get("items", []) if fact]   # a fact's term, not its sentence
    for screen in (data.get("screens") or {}).values():
        terms += [screen.get("title", "")] + [block.get("name", "") for block in screen.get("blocks", [])]
    return sorted({f'"{term}" is a term: write it in English, and only descriptions in the reader\'s language' for term in terms if foreign(term)})


def foreign(text):
    """A letter outside English's: Greek stays, since a term may carry a formula's symbol (λ)."""
    return any(character.isalpha() and not character.isascii() and "GREEK" not in unicodedata.name(character, "") for character in str(text))


QUOTED = re.compile(r'"[^"]*"|“[^”]*”|‘[^’]*’|«[^»]*»')
PARTICLES = "으로|로|은|는|이|가|을|를|과|와"
# a term's last sound, judged only where its last letter decides it
FINAL = [("ng", "c"), ("m", "c"), ("n", "c"), ("l", "l"), *((vowel, "v") for vowel in "aiouwy")]
# wrong particle -> right one, by the term's last sound: vowel, consonant, ㄹ (which takes 로, not 으로)
FIX = {"v": {"은": "는", "이": "가", "을": "를", "과": "와", "으로": "로"},
       "c": {"는": "은", "가": "이", "를": "을", "와": "과", "로": "으로"},
       "l": {"는": "은", "가": "이", "를": "을", "와": "과", "으로": "로"}}
POSITION = re.compile(r"(?<![가-힣])(위|아래|앞|다음)\s+(그림|표|식|그래프|칸)(?:처럼|에서|으로|[은는이가을를의에도과와로만]|[^가-힣]|$)")


def prose_fields(system_model):
    """(where, text) for each description; code, quote, payload, diff, tree and screens are verbatim, so left out."""
    data = system_model.document
    yield "next", data.get("next", "")
    yield "plan intent", data["plan"].get("intent", "")
    for scenario in data["scenarios"]:
        yield scenario["slug"], scenario.get("text", "")
        for step in walk_steps(scenario["walk"]):
            if isinstance(step, dict):
                yield f'{scenario["slug"]} step', step.get("does", "")
                yield f'{scenario["slug"]} step', step.get("expects", "")
    for operation in data["operations"] + data["rules"]:
        yield operation["slug"], operation.get("text", "")
    for level in data["levels"]:
        for owner in [level] + level["nodes"] + level["edges"] + level.get("triggers", []):
            where = owner.get("id", level["id"])
            yield where, owner.get("what", "")
            yield where, owner.get("why", "")
            for medium in owner.get("media", []):
                kind = medium.get("type")
                if kind in ("example", "pitfall"):
                    yield where, medium.get("text", "")
                elif kind == "checklist":
                    for item in medium.get("items", []):
                        yield where, str(item)
                elif kind == "facts":   # item[0] is the term, English
                    for item in medium.get("items", []):
                        for cell in item[1:]:
                            yield where, str(cell)
                elif kind == "insight":
                    for field in ("move", "vs", "gain"):
                        yield where, medium.get(field, "")


def sentences(text):
    """(sentence, masked) pairs: a sentence ends at . ? or ! before a space or the end; a quote is masked, so it
    never ends one and never fails."""
    masked = QUOTED.sub(lambda quote: "□" * len(quote.group()), text)
    out, start = [], 0
    for end in [match.end() for match in re.finditer(r"[.?!](?=\s|$)", masked)] + [len(text)]:
        if masked[start:end].strip():
            out.append((text[start:end].strip(), masked[start:end].strip()))
        start = end
    return out


def prose(system_model):
    """A Korean model's descriptions read as Korean: formal endings, particles that agree with an English term and
    sit against it, 수 있다 and 수 없다 apart, and no 위/아래/앞/다음 pointing at a figure."""
    if system_model.document.get("lang") != "ko":
        return []
    out = []
    for where, text in prose_fields(system_model):
        for sentence, mask in sentences(str(text)):
            end = mask.rstrip(".?!)]} ")
            found = []
            if end.endswith("요") or (end.endswith("다") and not end.endswith("니다")):
                found.append("register: end it with -니다 or -니까")
            for term, particle in re.findall(rf"([A-Za-z]+)({PARTICLES})(?![가-힣])", mask):
                kind = next((sound for suffix, sound in FINAL if term.lower().endswith(suffix)), None)
                if kind and particle in FIX[kind]:
                    found.append(f"particle: {term}{FIX[kind][particle]}, not {term}{particle}")
            found += [f"spacing: write {spaced_term}{spaced_particle} with no space" for spaced_term, spaced_particle in re.findall(rf"([A-Za-z]+)\s+({PARTICLES})(?![가-힣])", mask)]
            found += [f"spacing: write 수 {predicate} with a space" for predicate in re.findall(r"수(있|없)", mask)]
            found += [f"position: name the figure instead of {match.group(1)} {match.group(2)}" for match in POSITION.finditer(mask)
                      if not mask[:match.start()].rstrip().endswith("그림의")]
            out += [f'{where}: {finding} in "{sentence}"' for finding in found]
    return out


def facts(system_model):
    """Facts hold the system's own facts, never the diagram's plan: an item echoes the plan when it holds the
    whole intent text (ignoring case and spacing, in whatever language), or names two of the plan's views or the model's levels."""
    data, out = system_model.document, []
    squash = lambda value: re.sub(r"\s+", "", value.casefold())
    intent = squash(data["plan"].get("intent", ""))
    names = {name.casefold() for name in [view.get("name", "") for view in data["plan"].get("views", [])] + [level["title"] for level in data["levels"]] if name}
    for level in data["levels"]:
        for owner in [level] + level["nodes"] + level["edges"]:
            for medium in owner.get("media", []):
                if medium.get("type") != "facts":
                    continue
                for item in medium.get("items", []):
                    text = " ".join(map(str, item))
                    if (intent and intent in squash(text)) or sum(name in text.casefold() for name in names) >= 2:
                        where = owner.get("id", level["id"])
                        out.append(f'{level["id"]}: the facts on {where} restate the plan ("{item[0]}"); keep the plan for the hand-over and state the system\'s facts')
                        break
    return out


LINT = {"size", "phone", "depth", "prose"}

RULES = [
    ("names", "every term is English: titles, labels, media titles, fact terms, screen titles and block names", names),
    ("size", "a level has 2 to max_nodes (7) nodes", size),
    ("phone", f"a phone can draw the root: no two of its partitions joined at more than {LIMITS['partitionLinks']} pairs of nodes", phone),
    ("depth", "an overview's views feature the root and one level; no level is cut", depth),
    ("facts", "facts state the system's facts, never the plan: no item restates the intent or lists the views", facts),
    ("prose", "a Korean model's descriptions end in -니다 or -니까, put particles by the English term's last sound with no space, write 수 있다 apart, and never point at 위/아래/앞/다음 그림", prose),
]
CHECKS = {rule[0] for rule in RULES}


def model(system, view):
    """The joined model as the drawing checks read it, its plan the page's."""
    merged = merge(system, view)
    merged["plan"] = page_plan(merged)
    system_model = Model(merged)
    system_model.plan, system_model.strict = merged["plan"], set(merged["plan"]["strict"])
    return system_model


def run(system, view, only=None):
    """(name, problems, severity) per drawing check, the view's form first; only a view that does not fit its schema
    or names what the system lacks stops the rest."""
    wrong = shape(view, SCHEMA, "view") or attach(system, view)
    if wrong:
        return [("form", wrong, "error")]
    out = [("form", plan_problems(system, view), "error")] if not only or "form" in only else []
    system_model = model(system, view)
    for name, _, check in RULES:
        if not only or name in only:
            out.append((name, check(system_model), "lint" if name in LINT and name not in system_model.strict else "error"))
    return out

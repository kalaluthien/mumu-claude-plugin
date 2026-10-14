"""A zoom diagram's view of a system model: the view file (layout, views, depth, language, screens), how it joins
the system file into the model the page reads, and the checks of the drawing."""
import copy
import json
import pathlib
import re
import unicodedata

from system import plan as system_plan
from system.model import Model, levels_of, shape, walk_steps

ASSETS = pathlib.Path(__file__).resolve().parents[2] / "skills/show-me/references/zoom-diagram/assets"
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


def edge_key(L, e):
    """An edge's key within its level: from>to, and #label when two edges join the same pair."""
    twins = sum(1 for x in L["edges"] if (x["from"], x["to"]) == (e["from"], e["to"]))
    return f'{e["from"]}>{e["to"]}' + (f'#{e["label"]}' if twins > 1 else "")


def levels(data):
    """(level id, level) for every level: root, or the id of the node that opens it."""
    return [(opener or "root", L) for L, opener in levels_of(data)]


def split(m):
    """A whole model as (system, view): the view takes the drawing's keys, the system keeps the rest."""
    s, v = copy.deepcopy(m), {}
    for k in TOP:
        if k in s:
            v[k] = s.pop(k)
    p, vp = s.get("plan", {}), {}
    for k in PLAN_KEYS:
        if k in p:
            vp[k] = p.pop(k)
    if "strict" in p:
        vs = [c for c in p["strict"] if c in CHECKS]
        p["strict"] = [c for c in p["strict"] if c not in CHECKS]
        vp.update({"strict": vs} if vs else {})
        if not p["strict"]:
            del p["strict"]
    if "why" in p:
        vw = {k: p["why"].pop(k) for k in list(p["why"]) if k in PLAN_KEYS or (k == "strict" and "strict" in vp and "strict" not in p)}
        vp.update({"why": vw} if vw else {})
        if not p["why"]:
            del p["why"]
    if vp:
        v["plan"] = vp
    out = {}
    for lid, L in levels(s):
        nodes = {n["id"]: {k: n.pop(k) for k in NODE_KEYS if k in n} for n in L.get("nodes", [])}
        edges = {}
        for e in L.get("edges", []):
            d = {k: e.pop(k) for k in EDGE_KEYS if k in e}
            if d:
                edges[edge_key(L, e)] = d
        entry = ({"nodes": {i: d for i, d in nodes.items() if d}} if any(nodes.values()) else {}) | ({"edges": edges} if edges else {})
        if entry:
            out[lid] = entry
    if out:
        v["levels"] = out
    return s, v


def merge(s, v):
    """The whole model the page reads: the system's keys in its order, `next` and `lang` after `title`, `screens`
    before `level`; a node's x and y after its label and ui last; an edge's via last."""
    out = {}
    for k, val in s.items():
        if k == "level" and "screens" in v:
            out["screens"] = v["screens"]
        out[k] = copy.deepcopy(val)
        if k == "title":
            out.update({t: v[t] for t in ("next", "lang") if t in v})
    if "plan" in v:
        p, vp = out.setdefault("plan", {}), v["plan"]
        why, strict = {**p.get("why", {}), **vp.get("why", {})}, p.get("strict", []) + vp.get("strict", [])
        p.update({k: x for k, x in vp.items() if k not in ("why", "strict")})
        if strict:
            p["strict"] = strict
        if why:
            p.pop("why", None)
            p["why"] = why
    given = v.get("levels", {})
    for lid, L in levels(out):
        entry = given.get(lid, {})
        if "nodes" in L:
            nodes = []
            for n in L["nodes"]:
                d, keys = entry.get("nodes", {}).get(n["id"], {}), list(n)
                head = keys[:keys.index("label") + 1] if "label" in keys else keys[:1]
                new = {k: n[k] for k in head} | {k: d[k] for k in ("x", "y") if k in d}
                new |= {k: n[k] for k in keys if k not in new}
                nodes.append(new | ({"ui": d["ui"]} if "ui" in d else {}))
            L["nodes"] = nodes
        for e in L.get("edges", []):
            e.update(entry.get("edges", {}).get(edge_key(L, e), {}))
    return out


def page_plan(m):
    """The plan the page reads, in the order it has always had: system and view defaults with the model's plan."""
    defaults = {k: d[0] for k, d in system_plan.DEFAULTS.items()} | {k: d[0] for k, d in DEFAULTS.items()}
    plan = {k: copy.deepcopy(defaults[k]) for k in PAGE_ORDER}
    plan.update(m.get("plan") or {})
    if isinstance(plan["show"], dict):
        plan["show"] = {**DEFAULTS["show"][0], **plan["show"]}
    return plan


def attach(s, v):
    """Where the view names something the system lacks: a level, node, edge or screen block."""
    out, by = [], dict(levels(s))
    screens = v.get("screens") or {}
    for lid, entry in (v.get("levels") or {}).items():
        L = by.get(lid)
        if L is None:
            out.append(f"view: levels.{lid} is no level (root, or a node that opens one)")
            continue
        ids, keys = {n["id"] for n in L.get("nodes", [])}, {edge_key(L, e) for e in L.get("edges", [])}
        out += [f"view: levels.{lid}.nodes.{n} is no node of that level" for n in entry.get("nodes", {}) if n not in ids]
        out += [f"view: levels.{lid}.edges.{k} is no edge of that level (from>to, #label for twins)" for k in entry.get("edges", {}) if k not in keys]
        for n, d in entry.get("nodes", {}).items():
            ui = d.get("ui")
            if ui and not (ui["screen"] in screens and ui["block"] in {b["id"] for b in screens[ui["screen"]]["blocks"]}):
                out.append(f"{n}: ui points at no screen block")
    return out


def plan_problems(s, v):
    """What the schemas cannot say about the view's plan: every expected view is drawn or explained, deep nodes open
    a level, shallow ones do not, strict names drawing checks, every changed default says why, and `next` says what
    the reader does after."""
    out, given = [], v.get("plan") or {}
    opens = {lid for lid, _ in levels(s)} - {"root"}
    nodes = {n["id"] for _, L in levels(s) for n in L.get("nodes", [])}
    if not given.get("views"):
        out.append("plan: list the views a practitioner of this domain expects (views)")
    for x in given.get("views") or []:
        if ("level" in x) == ("why" in x):
            out.append(f'plan: view {x.get("name")} is drawn by a level or left out with why, one of the two')
        elif "level" in x and x["level"] != "root" and x["level"] not in opens:
            out.append(f'plan: view {x.get("name")} names no level {x["level"]}')
    out += [f"plan: {x} is no node" for x in given.get("deep", []) + given.get("shallow", []) if x not in nodes]
    out += [f"plan: deep {n} opens no level" for n in given.get("deep", []) if n in nodes and n not in opens]
    out += [f"plan: {n} is shallow, so it opens no level" for n in given.get("shallow", []) if n in opens]
    out += [f"plan: strict {c} is no drawing check" for c in given.get("strict", []) if c not in CHECKS]
    changed = [k for k in given if k not in ("views", "why") and given[k] != DEFAULTS[k][0]]
    out += [f"plan: say why {k} changed (in why)" for k in changed if k not in (given.get("why") or {})]
    if not v.get("next", "").strip():
        out.append("`next` is empty: write the reader's next action or choice in one sentence")
    return out


def size(M):
    out = []
    for L in M.m["levels"]:
        n = len(L["nodes"])
        if n > M.plan["max_nodes"]:
            out.append(f'{L["id"]}: {n} nodes; group those that work alike and open them below')
        if L.get("parent") and n < 2:
            out.append(f'{L["id"]}: opens with {n} node; merge it into {L["parent"]}')
    return out


def phone(M):
    """A phone's root is laid out again in two columns or one, so the author's columns never decide whether it fits.
    Partitions then stack as bands of rows, and two rows of two cells join by at most three lines that do not cross
    (two straight down, one across); more links between two partitions detour round the sides and meet. Limits in
    assets/phone-limits.json, shared with the engine; render measures the fit itself."""
    out = []
    for L in M.m["levels"]:
        if L.get("parent") or not L.get("partitions"):
            continue
        part = {n["id"]: n.get("partition") for n in L["nodes"]}
        links = {}
        for e in L["edges"]:
            a, b = part.get(e["from"]), part.get(e["to"])
            if a != b and a and b:   # a node outside every partition is the partitions check's to report
                links.setdefault(tuple(sorted((a, b))), set()).add(frozenset((e["from"], e["to"])))
        for (a, b), pairs in sorted(links.items()):
            if len(pairs) > LIMITS["partitionLinks"]:
                out.append(f'{L["id"]}: partitions {a} and {b} are joined at {len(pairs)} pairs of nodes, more than the '
                           f'{LIMITS["partitionLinks"]} a phone can draw apart; route some through one node or open them in a level below')
    return out


def depth(M):
    """Depth picks which levels the views feature; the page keeps every level the model holds."""
    if M.plan["depth"] != "overview":
        return []
    return [f'view {v.get("name")}: an overview features the root and one level, and {v["level"]} lies {M.depth(v["level"])} below'
            for v in M.plan.get("views") or [] if v.get("level") in M.levels and M.depth(v["level"]) > 1]


def names(M):
    """Every term is English whatever the reader's language; only descriptions follow it."""
    m = M.m
    terms = [m.get("title", "")] + [t for L in m["levels"] for t in [L.get("title", "")]
             + [x.get("label", "") for x in L["nodes"] + L["edges"] + L.get("triggers", []) + L.get("partitions", []) + L.get("regions", [])]]
    for md in [md for L in m["levels"] for o in [L] + L["nodes"] + L["edges"] for md in o.get("media", [])]:
        terms.append(md.get("title", ""))
        if md.get("type") == "facts":
            terms += [i[0] for i in md.get("items", []) if i]   # a fact's term, not its sentence
    for sc in (m.get("screens") or {}).values():
        terms += [sc.get("title", "")] + [b.get("name", "") for b in sc.get("blocks", [])]
    return sorted({f'"{t}" is a term: write it in English, and only descriptions in the reader\'s language' for t in terms if foreign(t)})


def foreign(text):
    """A letter outside English's: Greek stays, since a term may carry a formula's symbol (λ)."""
    return any(c.isalpha() and not c.isascii() and "GREEK" not in unicodedata.name(c, "") for c in str(text))


QUOTED = re.compile(r'"[^"]*"|“[^”]*”|‘[^’]*’|«[^»]*»')
PARTICLES = "으로|로|은|는|이|가|을|를|과|와"
# a term's last sound, judged only where its last letter decides it
FINAL = [("ng", "c"), ("m", "c"), ("n", "c"), ("l", "l"), *((v, "v") for v in "aiouwy")]
# wrong particle -> right one, by the term's last sound: vowel, consonant, ㄹ (which takes 로, not 으로)
FIX = {"v": {"은": "는", "이": "가", "을": "를", "과": "와", "으로": "로"},
       "c": {"는": "은", "가": "이", "를": "을", "와": "과", "로": "으로"},
       "l": {"는": "은", "가": "이", "를": "을", "와": "과", "으로": "로"}}
POSITION = re.compile(r"(?<![가-힣])(위|아래|앞|다음)\s+(그림|표|식|그래프|칸)(?:처럼|에서|으로|[은는이가을를의에도과와로만]|[^가-힣]|$)")


def prose_fields(M):
    """(where, text) for each description; code, quote, payload, diff, tree and screens are verbatim, so left out."""
    m = M.m
    yield "next", m.get("next", "")
    yield "plan intent", m["plan"].get("intent", "")
    for s in m["scenarios"]:
        yield s["slug"], s.get("text", "")
        for st in walk_steps(s["walk"]):
            if isinstance(st, dict):
                yield f'{s["slug"]} step', st.get("does", "")
                yield f'{s["slug"]} step', st.get("expects", "")
    for o in m["operations"] + m["rules"]:
        yield o["slug"], o.get("text", "")
    for L in m["levels"]:
        for owner in [L] + L["nodes"] + L["edges"] + L.get("triggers", []):
            where = owner.get("id", L["id"])
            yield where, owner.get("what", "")
            yield where, owner.get("why", "")
            for md in owner.get("media", []):
                t = md.get("type")
                if t in ("example", "pitfall"):
                    yield where, md.get("text", "")
                elif t == "checklist":
                    for item in md.get("items", []):
                        yield where, str(item)
                elif t == "facts":   # item[0] is the term, English
                    for item in md.get("items", []):
                        for x in item[1:]:
                            yield where, str(x)
                elif t == "insight":
                    for f in ("move", "vs", "gain"):
                        yield where, md.get(f, "")


def sentences(text):
    """(sentence, masked) pairs: a sentence ends at . ? or ! before a space or the end; a quote is masked, so it
    never ends one and never fails."""
    masked = QUOTED.sub(lambda q: "□" * len(q.group()), text)
    out, start = [], 0
    for e in [x.end() for x in re.finditer(r"[.?!](?=\s|$)", masked)] + [len(text)]:
        if masked[start:e].strip():
            out.append((text[start:e].strip(), masked[start:e].strip()))
        start = e
    return out


def prose(M):
    """A Korean model's descriptions read as Korean: formal endings, particles that agree with an English term and
    sit against it, 수 있다 and 수 없다 apart, and no 위/아래/앞/다음 pointing at a figure."""
    if M.m.get("lang") != "ko":
        return []
    out = []
    for where, text in prose_fields(M):
        for sent, mask in sentences(str(text)):
            end = mask.rstrip(".?!)]} ")
            found = []
            if end.endswith("요") or (end.endswith("다") and not end.endswith("니다")):
                found.append("register: end it with -니다 or -니까")
            for term, par in re.findall(rf"([A-Za-z]+)({PARTICLES})(?![가-힣])", mask):
                kind = next((k for suffix, k in FINAL if term.lower().endswith(suffix)), None)
                if kind and par in FIX[kind]:
                    found.append(f"particle: {term}{FIX[kind][par]}, not {term}{par}")
            found += [f"spacing: write {t}{p} with no space" for t, p in re.findall(rf"([A-Za-z]+)\s+({PARTICLES})(?![가-힣])", mask)]
            found += [f"spacing: write 수 {w} with a space" for w in re.findall(r"수(있|없)", mask)]
            found += [f"position: name the figure instead of {m.group(1)} {m.group(2)}" for m in POSITION.finditer(mask)
                      if not mask[:m.start()].rstrip().endswith("그림의")]
            out += [f'{where}: {f} in "{sent}"' for f in found]
    return out


def pairs(text):
    s = re.sub(r"\s+", "", text.casefold())
    return {s[i:i + 2] for i in range(len(s) - 1)}


def facts(M):
    """Facts hold the system's own facts, never the diagram's plan: an item echoes the plan when it holds a third of
    the intent's character pairs, in whatever language, or names two of the plan's views or the model's levels."""
    m, out = M.m, []
    intent = pairs(m["plan"].get("intent", ""))
    names = {x.casefold() for x in [v.get("name", "") for v in m["plan"].get("views", [])] + [L["title"] for L in m["levels"]] if x}
    for L in m["levels"]:
        for owner in [L] + L["nodes"] + L["edges"]:
            for md in owner.get("media", []):
                if md.get("type") != "facts":
                    continue
                for item in md.get("items", []):
                    text = " ".join(map(str, item))
                    if (intent and len(pairs(text) & intent) * 3 >= len(intent)) or sum(n in text.casefold() for n in names) >= 2:
                        where = owner.get("id", L["id"])
                        out.append(f'{L["id"]}: the facts on {where} restate the plan ("{item[0]}"); keep the plan for the hand-over and state the system\'s facts')
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
CHECKS = {r[0] for r in RULES}


def model(s, v):
    """The joined model as the drawing checks read it, its plan the page's."""
    m = merge(s, v)
    m["plan"] = page_plan(m)
    M = Model(m)
    M.plan, M.strict = m["plan"], set(m["plan"]["strict"])
    return M


def run(s, v, only=None):
    """(name, problems, severity) per drawing check, the view's form first; only a view that does not fit its schema
    or names what the system lacks stops the rest."""
    wrong = shape(v, SCHEMA, "view") or attach(s, v)
    if wrong:
        return [("form", wrong, "error")]
    out = [("form", plan_problems(s, v), "error")] if not only or "form" in only else []
    M = model(s, v)
    for name, _, fn in RULES:
        if not only or name in only:
            out.append((name, fn(M), "lint" if name in LINT and name not in M.strict else "error"))
    return out

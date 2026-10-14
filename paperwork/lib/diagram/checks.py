"""Model checks: each takes a Model and returns the problems it found, each a sentence that says what to fix."""
import re
import unicodedata

from . import formula as F
from . import plan as params
from . import prover as A
from .model import LIMITS, places, plan, split_top, walk_steps

NODE_MEDIA, EDGE_MEDIA = {"tree", "checklist"}, {"diff", "payload"}
first_word = lambda t: t.strip().split()[0].lower() if t and t.strip() else ""
plain_verb = lambda w: not ((w.endswith("ed") and not w.endswith("eed")) or w.endswith("ing") or (w.endswith("s") and not w.endswith("ss")))


def form(M):
    """The file read as a model: every reference points at something (model.parse), the plan holds together, and `next` says what the reader does after."""
    empty_next = [] if M.m.get("next", "").strip() else ["`next` is empty: write the reader's next action or choice in one sentence"]
    return M.parse_problems + params.problems(M.m, M.child, [r[0] for r in RULES]) + empty_next


def steps(M):
    out = []
    for s in M.m["scenarios"]:
        for k, st in enumerate(walk_steps(s["walk"])):
            if not (isinstance(st, dict) and str(st.get("does", "")).strip() and str(st.get("expects", "")).strip()):
                out.append(f'{s["slug"]}: step {k + 1} says what it does and what it expects ({{"place", "does", "expects"}})')
            elif len(places(st)) > 1 and not all(M.kind_of.get(x) == "schema" and M.node_level.get(x) == M.node_level.get(places(st)[0]) for x in places(st)):
                out.append(f'{s["slug"]}: step {k + 1} is at several nodes, so they are parts of one component level')
        out += M.walks[s["slug"]][1]
    return out


def scoped(M):
    out = []
    for slug, h in M.home.items():
        sc = next(s for s in M.m["scenarios"] if s["slug"] == slug)
        climb = [x for x in plan(sc["walk"])[0] if x in M.nodes and h not in M.ancestors(M.node_level[x])]
        if climb:
            out.append(f'{slug}: starts in {h} but climbs above it at {climb[0]}')
    # every level needs Scenarios of its own, or (plan scenarios: entry) only the root and levels things enter from outside
    own = [L for L in M.m["levels"] if M.plan["scenarios"] == "every" or not L.get("parent") or L.get("triggers")]
    out += [f'{L["id"]}: give this level a Scenario of its own' for L in own if L["id"] not in M.home.values()]
    return out


def coverage(M):
    used = set().union(*M.footprint.values()) if M.footprint else set()
    orphans = sorted(M.elements() - used)
    return [f"no Scenario uses {k} {x}; drop it or name the use it serves" for k, x in orphans]


def basis(M):
    out = []
    for s, f in M.footprint.items():
        subs = [t for t, g in M.footprint.items() if t != s and g <= f and M.home.get(t) == M.home.get(s)]
        if subs and set().union(*(M.footprint[t] for t in subs)) == f:
            out.append(f"{s} is the union of {subs}; drop it")
    return out


def placement(M):
    out = []
    event_ops = {x for L in M.m["levels"] if L["kind"] == "state" for e in L["edges"] + L.get("triggers", []) for x in e.get("ops", [])}
    edge_ops = {x for _, e in list(M.edges.values()) + list(M.trigs.values()) for x in e.get("ops", [])}
    sits = M.sits()
    for o in M.ops:
        if o not in sits:
            out.append(f"{o}: place it on a node or an event")
        elif o in edge_ops - event_ops:
            out.append(f"{o}: only an event edge carries an operation")
    out += [f"{i}: place it on a node or an edge" for i in M.rules if i not in sits]
    return out


def explained(M):
    out = []
    for k, (L, e) in M.edges.items():
        if not (e.get("what") or e.get("ops") or e.get("rules") or M.is_abstract(L, e["to"])):
            out.append(f'{L["id"]}: {e["from"]}>{e["to"]} says nothing; give it a sentence, an operation or a guard')
    for k, (L, t) in M.trigs.items():
        if not (t.get("what") or t.get("ops") or t.get("rules")):
            out.append(f'{L["id"]}: trigger {t["label"]} says nothing')
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


def mechanism(M):
    out = []
    walks = lambda tr: any(M.kind_of.get(x) in ("workflow", "state") for x in tr)
    if not any(L["kind"] in ("workflow", "state") for L in M.m["levels"]):
        return out   # nothing runs: a body of knowledge is claims and what they rest on
    rooted = [s for s in M.m["scenarios"] if M.home.get(s["slug"]) == M.root]
    out += [f'{s["slug"]}: a root Scenario walks no activity or state' for s in rooted if not walks(plan(s["walk"])[0])]
    parts = [x for x, k in M.kind_of.items() if k == "schema"]
    if not parts:
        out.append("no component level: show what the system is made of")
    out += [f"{x}: in no root Scenario that also walks an activity or state" for x in parts
            if not any(x in plan(s["walk"])[0] and walks(plan(s["walk"])[0]) for s in rooted)]
    return out


def partitions(M):
    out = []
    for L in M.m["levels"]:
        P = {p["id"] for p in L.get("partitions", [])}
        if not P:
            continue
        if len(P) < 2:
            out.append(f'{L["id"]}: one partition says nothing; drop it')
        out += [f'{L["id"]}: put {n["id"]} in a partition' for n in L["nodes"] if n.get("partition") not in P]
        side = {n["id"]: n.get("partition") for n in L["nodes"]}
        if L["kind"] == "state":   # partitions of a state level are orthogonal regions (Harel): each runs on its own
            inits = [L["initial"]] if isinstance(L.get("initial"), str) else L.get("initial") or []
            for p in P:
                k = sum(1 for i in inits if side.get(i) == p)
                if k != 1:
                    out.append(f'{L["id"]}: region {p} needs exactly one initial state, has {k}')
            out += [f'{L["id"]}: event {e["label"]} leaves its region; regions meet only through syncs' for e in L["edges"] if side.get(e["from"]) != side.get(e["to"])]
            continue
        for e in L["edges"]:
            contract = e.get("rules") or e.get("ops") or any(x.get("type") == "payload" for x in e.get("media", []))
            if L["kind"] != "schema" and side.get(e["from"]) != side.get(e["to"]) and not contract:
                out.append(f'{L["id"]}: {e["from"]}>{e["to"]} crosses partitions; give it a payload, guard or operation')
    return out


GATES = {"checking", "reviewing", "validating", "verifying", "testing", "judging", "approving", "gating", "evaluating"}


def quantities(M):
    """Quantities add up: a count is what enters and what leaves it, a node that holds nothing passes on what it
    receives, a flow into or out of a stock is in the stock's unit, and a deadline says what happens when it passes."""
    out, same = [], lambda a, b: abs(a - b) <= 1e-9 * max(1, abs(a), abs(b))
    for L in M.m["levels"]:
        for e in L["edges"]:
            q = e.get("qty")
            if q and q["kind"] not in ("flow", "count", "delay"):
                out.append(f'{L["id"]}: {e["label"]} carries a flow, a count or a delay, not a {q["kind"]}')
            if q and q["kind"] == "delay" and not any(x is not e and x["from"] == e["from"] and "failure" in x.get("mark", []) for x in L["edges"]):
                out.append(f'{L["id"]}: {e["label"]} has a deadline; draw what happens when it passes, an edge from {e["from"]} marked failure')
        for n in L["nodes"]:
            q = n.get("qty")
            if q and q["kind"] not in ("stock", "count", "capacity"):
                out.append(f'{L["id"]}: {n["label"]} holds a stock, a count or a capacity, not a {q["kind"]}')
                continue
            sides = {"in": [e for e in L["edges"] if e["to"] == n["id"] != e["from"]],
                     "out": [e for e in L["edges"] if e["from"] == n["id"] != e["to"]]}
            if q and q["kind"] == "stock":
                out += [f'{L["id"]}: {e["label"]} moves {e["qty"]["unit"]}, not the {q["unit"]} that {n["label"]} holds'
                        for es in sides.values() for e in es
                        if e.get("qty", {}).get("kind") == "flow" and e["qty"]["unit"].split("/")[0].strip() != q["unit"]]
                continue
            told = {k: [e["qty"] for e in es if e.get("qty", {}).get("kind") in ("flow", "count")] for k, es in sides.items()}
            full = {k: v for k, v in told.items() if v and len(v) == len(sides[k]) and len({x.get("unit", "") for x in v}) == 1}
            total = {k: sum(x["value"] for x in v) for k, v in full.items()}
            if q and q["kind"] == "count":
                out += [f'{L["id"]}: {n["label"]} counts {q["value"]}, but {total[k]} {"enter" if k == "in" else "leave"}'
                        for k in total if not same(total[k], q["value"])]
            elif len(total) == 2 and full["in"][0].get("unit", "") == full["out"][0].get("unit", "") and not same(total["in"], total["out"]):
                out.append(f'{L["id"]}: {n["label"]} holds nothing, yet {total["in"]} enter and {total["out"]} leave')
    return out


def paths(M):
    """A workflow or state level shows its main path, and every gate shows how it fails."""
    out = []
    for L in M.m["levels"]:
        if L["kind"] == "schema":
            continue
        if not any("happy" in e.get("mark", []) for e in L["edges"]):
            out.append(f'{L["id"]}: mark the main path happy')
        parent = L.get("parent") and M.level_of(L["parent"])
        port_fail = {fr for f in L.get("out", []) for fr in ([f["from"]] if isinstance(f.get("from"), str) else f.get("from", []))
                     if parent and any(e["label"] == f.get("edge") and "failure" in e.get("mark", []) for e in parent["edges"])}
        for n in L["nodes"]:
            if first_word(n["label"]) in GATES:
                fails = any(e["from"] == n["id"] and "failure" in e.get("mark", []) for e in L["edges"]) or n["id"] in port_fail
                if not fails:
                    out.append(f'{L["id"]}: {n["label"]} is a gate; draw how it fails (a failure edge or port)')
    return out


def syncs(M):
    """Regions meet only through syncs (Meng and Jackson): when an event in one region, where a state holds, then an event in another."""
    out = []
    for L in M.m["levels"]:
        region = {n["id"]: n.get("partition") for n in L["nodes"]}
        events = {e["label"]: region.get(e["from"]) for e in L["edges"]}
        for y in L.get("syncs", []):
            name = y.get("name", "?")
            if L["kind"] != "state" or not L.get("partitions"):
                out.append(f'{L["id"]}: sync {name} joins regions, so it sits on a state level with partitions')
            elif events[y["when"]] == events[y["then"]]:
                out.append(f'{L["id"]}: sync {name} joins two events of one region; join regions')
            if not y.get("what"):
                out.append(f'{L["id"]}: sync {name} says nothing; give it a sentence')
    return out


def depth(M):
    if M.plan["depth"] == "overview":
        deepest = max(M.depth(L["id"]) for L in M.m["levels"])
        if deepest > 1:
            return [f"overview stops one level below the root, found {deepest}"]
    return []


def naming(M):
    out = []
    for L in M.m["levels"]:
        k = L["kind"]
        for n in L["nodes"]:
            if k == "workflow" and not first_word(n["label"]).endswith("ing"):
                out.append(f'{L["id"]}: activity "{n["label"]}" starts with a verb in -ing')
            if n.get("abstract") and k != "schema":
                out.append(f'{L["id"]}: only a component can be abstract')
        for e in L["edges"]:
            w = first_word(e.get("label", ""))
            if k == "schema" and not w.endswith("s"):
                out.append(f'{L["id"]}: relation "{e["label"]}" starts with a present-tense verb (uses, opens)')
            if k == "state" and not plain_verb(w):
                out.append(f'{L["id"]}: event "{e["label"]}" starts with a plain verb (merge, mark ready)')
            if k == "workflow" and w.endswith("ing") and not e.get("is"):
                out.append(f'{L["id"]}: artifact "{e["label"]}" is a noun phrase')
            if M.is_abstract(L, e["from"]) and not M.is_abstract(L, e["to"]):
                out.append(f'{L["id"]}: abstract {e["from"]} cannot depend on concrete {e["to"]}')
        for t in L.get("triggers", []):
            w = first_word(t.get("label", ""))
            if (k == "state" and not plain_verb(w)) or (k == "workflow" and w.endswith("ing")):
                out.append(f'{L["id"]}: trigger "{t["label"]}" is named like the level\'s edges')
        for x in L["nodes"] + L["edges"] + L.get("triggers", []):
            if {"happy", "failure"} <= set(x.get("mark", [])):
                out.append(f'{L["id"]}: {x.get("label")} is marked both happy and failure')
    return out


def names(M):
    """Every name the module declares is an Alloy name (ASCII, starting with a letter) clear of Alloy's keywords
    and the translation's own words; caught here, before the slow Alloy run."""
    m, found = M.m, []
    for L in m["levels"]:
        found += [(A.ident(n["label"]), n["label"]) for n in L["nodes"]]
        found += [(A.lower(x["label"]), x["label"]) for x in L["edges"] + L.get("triggers", []) if L["kind"] == "state" and x.get("label")]
        found += [((A.ident if a.split(":", 1)[-1].strip() == "Bool" else str)(a.split(":")[0].strip()), a) for n in L["nodes"] for a in n.get("attrs", [])]
        found += [(A.lower(e["label"]), e["label"]) for e in L["edges"] if L["kind"] in ("schema", "workflow") and e.get("label")]
        if L["kind"] == "workflow":
            found.append((A.ident(L["title"]), L["title"]))
    for o in m["operations"]:
        if o["slug"] in M.sigs:
            found.append((M.sigs[o["slug"]][2], o["slug"]))
            found += [(p, o["slug"]) for p in M.sigs[o["slug"]][1]]
    found += [(A.lower(i["slug"]), i["slug"]) for i in m["rules"]]
    found += [(t, t) for t in (m.get("types") or {})]
    for t in [x for L in m["levels"] for n in L["nodes"] for x in n.get("attrs", [])] + [o.get("sig", "") for o in m["operations"]] + list((m.get("types") or {}).values()):
        for lit in re.findall(r"\{([^}]*)\}", str(t)):
            found += [(v.strip(), lit) for v in lit.split(",")]
    out = {f'"{n}" in {where} is a word Alloy or the translation reserves; rename it' for n, where in found if n in F.RESERVED}
    out |= {f'{where} gives no Alloy name ("{n}"); write it in ASCII letters' for n, where in found if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", str(n))}
    # terms are English whatever the reader's language; only descriptions follow it
    terms = [m.get("title", "")] + [t for L in m["levels"] for t in [L.get("title", "")]
             + [x.get("label", "") for x in L["nodes"] + L["edges"] + L.get("triggers", []) + L.get("partitions", []) + L.get("regions", [])]]
    for md in [md for L in m["levels"] for o in [L] + L["nodes"] + L["edges"] for md in o.get("media", [])]:
        terms.append(md.get("title", ""))
        if md.get("type") == "facts":
            terms += [i[0] for i in md.get("items", []) if i]   # a fact's term, not its sentence
    for sc in (m.get("screens") or {}).values():
        terms += [sc.get("title", "")] + [b.get("name", "") for b in sc.get("blocks", [])]
    out |= {f'"{t}" is a term: write it in English, and only descriptions in the reader\'s language' for t in terms if foreign(t)}
    return sorted(out)


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


def media(M):
    out = []
    words = lambda z: set(re.findall(r"\w{2,}", z))
    for L in M.m["levels"]:
        hosts = [(n, "node") for n in L["nodes"]] + [(e, "edge") for e in L["edges"]] + [(L, "level")]
        insights = 0
        for x, where in hosts:
            for md in x.get("media", []):
                t = md.get("type")
                if (t in NODE_MEDIA and where == "edge") or (t in EDGE_MEDIA and where == "node"):
                    out.append(f'{L["id"]}: {t} does not sit on a {where}')
                if t != "insight":
                    continue
                insights += 1
                here = set(M.ops) | set(M.rules) if where == "level" else set(x.get("ops", [])) | set(x.get("rules", []))
                miss = [f for f in ("move", "vs", "gain", "rule") if not str(md.get(f, "")).strip()]
                mv, desc = words(md.get("move", "")), words(x.get("what", x.get("why", "")))
                if miss:
                    out.append(f'{L["id"]}: an insight needs move, vs, gain and rule (missing {miss})')
                elif md["rule"] not in here:
                    out.append(f'{L["id"]}: the insight\'s rule {md["rule"]} must sit on the same node or edge')
                elif mv and len(mv & desc) / len(mv) > 0.5:
                    out.append(f'{L["id"]}: an insight names what is distinctive, not what the description says')
        if insights > 1:
            out.append(f'{L["id"]}: {insights} insights; keep the most distinctive one')
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


def unique_names(M):
    m = M.m
    norm = lambda t: re.sub(r"[\s_-]+", " ", t.strip().lower())
    linked = {(L["id"], e["label"]) for L in m["levels"] for e in L["edges"] if e.get("is")}
    names = ([("scenario", s["slug"]) for s in m["scenarios"]] + [("operation", o["slug"]) for o in m["operations"]]
             + [("rule", i["slug"]) for i in m["rules"]] + [("level", L["title"]) for L in m["levels"]]
             + [("node", n["label"]) for n in M.nodes.values()]
             + [("partition", lab) for lab in {p["label"] for L in m["levels"] for p in L.get("partitions", [])}]   # one owner may recur across levels
             + [("edge", lab) for lab in {e["label"] for L in m["levels"] for e in L["edges"]   # a verb may recur
                                          if e.get("label") and not M.is_abstract(L, e["to"]) and (L["id"], e["label"]) not in linked}]
             + [("trigger", t["label"]) for L in m["levels"] for t in L.get("triggers", [])]
             + [("sync", y["name"]) for L in m["levels"] for y in L.get("syncs", []) if y.get("name")])
    seen, out = {}, []
    for kind, name in names:
        seen.setdefault(norm(name), []).append(f"{kind} '{name}'")
    out += [" = ".join(v) + "; rename one" for v in seen.values() if len(v) > 1]
    for L in m["levels"]:
        for e in L["edges"]:
            tgt = M.nodes.get(e.get("is"))
            if e.get("is") and not (L["kind"] == "workflow" and tgt and M.kind_of[e["is"]] == "schema" and A.singular(A.ident(tgt["label"])) == A.singular(A.ident(e["label"]))):
                out.append(f'{L["id"]}: {e["from"]}>{e["to"]} "is" names a component with the same label')
    return out


def typed(M):
    """Types are exact names the module declares; signatures, attributes and relations agree with the drawing."""
    W = A.World(M)
    out = list(W.problems)
    for t, txt in (M.m.get("types") or {}).items():
        if not re.sub(r"^\s*\{[^}]*\}", "", str(txt)).strip():
            out.append(f"type {t}: say in a sentence what it is")
    for o in M.m["operations"]:
        sl = o["slug"]
        if sl not in M.sigs:
            out.append(f'{sl}{o.get("sig", "")}: write Receiver.verb and (name: Type, …) → Result')
            continue
        params = split_top(re.match(r"\s*\((.*)\)", o["sig"]).group(1))
        out += [f"{sl}: parameter {p} needs name: Type" for p in params if not re.fullmatch(r"[a-z][A-Za-z0-9]*\s*:\s*.+", p)]
    for L in M.m["levels"]:
        for n in L["nodes"]:
            ops = [x for x in n.get("ops", []) if x in M.sigs]
            if L["kind"] == "schema":
                out += [f'{L["id"]}: {x} sits on {n["label"]}, so its receiver is {A.ident(n["label"])}' for x in ops if M.sigs[x][0] != A.ident(n["label"])]
            if L["kind"] == "workflow" and ops:
                outs = [e["label"] for e in L["edges"] if e["from"] == n["id"]]
                made = {r for x in ops for r in A.Type(re.search(r"→\s*(.+)$", M.ops[x]["sig"]).group(1)).refs()}
                if outs and not any(made & A.artifact_types(l) for l in outs):
                    out.append(f'{L["id"]}: {n["label"]} hands on {", ".join(outs)}, but none of its operations returns it')
            for a in n.get("attrs", []):
                ma = re.fullmatch(r"([a-z][A-Za-z0-9]*)\s*:\s*(.+)", a)
                if not ma or L["kind"] != "schema":
                    out.append(f'{n["label"]}: attribute "{a}" is name: Type on a component')
        if L["kind"] != "schema":
            continue
        comp = {A.ident(n["label"]): n for n in L["nodes"]}
        attrs = {n["id"]: [(nm, t) for _, nn, nm, t in W._attrs() if nn is n] for n in L["nodes"]}
        for n in L["nodes"]:
            for nm, t in attrs[n["id"]]:
                peers = [comp[r] for r in t.names if len(t.names) == 1 and not t.tuple and r in comp and comp[r] is not n and not comp[r].get("abstract")]
                for p in peers:
                    if not any(e["from"] == n["id"] and e["to"] == p["id"] for e in L["edges"]):
                        out.append(f'{n["label"]}.{nm} points at {p["label"]}; draw the relation')
        for e in L["edges"]:
            if M.is_abstract(L, e["to"]):
                continue
            to = A.ident(M.nodes[e["to"]]["label"])
            cands = [nm for nm, t in attrs[e["from"]] if to in t.refs()]
            if e.get("attr"):
                if e["attr"] not in cands:
                    out.append(f'{L["id"]}: relation {e["label"]} names attribute {e["attr"]}, which does not point at {M.nodes[e["to"]]["label"]}')
            elif len(cands) > 1:
                out.append(f'{L["id"]}: relation {e["label"]} could be {cands}; name one with attr')
    return out


def vocabulary(M):
    """Formulas are Alloy over the module's names, with every variable bound and no name hidden."""
    W, out = A.World(M), []
    for i in M.m["rules"]:
        out += W.check_formula(i["formula"], i["slug"])
    for sl, op in list(W.change.items()) + list(W.query.items()):
        extra = ["self"] + [p for p, _, _ in op["params"]] + (["result"] if op["rdecl"] else [])
        for part in ("pre", "post"):
            if op.get(part):
                out += W.check_formula(op[part], f"{sl} {part}", extra)
    for L in M.m["levels"]:
        if L.get("init"):
            out += W.check_formula(L["init"], f'{L["id"]} init')
    return out


def balanced(M):
    out = []
    for L in M.m["levels"]:
        P = L.get("parent") and M.level_of(L["parent"])
        if not (P and P["kind"] == "workflow" and L["kind"] == "workflow"):
            continue
        ids = {n["id"] for n in L["nodes"]}
        need_in = sorted({e["label"] for e in P["edges"] if e["to"] == L["parent"]} | {t["label"] for t in P.get("triggers", []) if t["to"] == L["parent"]})
        need_out = sorted({e["label"] for e in P["edges"] if e["from"] == L["parent"]})
        got_in = sorted(f.get("edge") for f in L.get("in", []) if f.get("to") in ids)
        got_out = sorted(f.get("edge") for f in L.get("out", []) if f.get("from") and set([f["from"]] if isinstance(f["from"], str) else f["from"]) <= ids)
        if (got_in, got_out) != (need_in, need_out):
            out.append(f'{L["id"]}: in {got_in} should be {need_in}; out {got_out} should be {need_out}')
    return out


def alloy(M):
    """Translate the model to Alloy 6 and let Alloy answer: the rules agree, each is independent, every must rule
    holds under the behaviour, every Scenario and failure path can happen. Commands whose text is unchanged reuse
    their last answer. Skipped, and said so, when Java or Alloy is missing."""
    M.alloy_notes = []
    if M.plan["prove"] == "off":
        M.alloy_status = "skipped: the plan says prove: off"
        return []
    if not A.jar():
        M.alloy_status = "skipped: no Alloy (set ALLOY_JAR or run `make-diagram.py alloy --fetch`)"
        return []
    try:
        W, C, res = A.solve(M)
    except RuntimeError as e:
        return [f"Alloy refused the translation: {e}"]
    probs, notes = A.verdicts(M, W, C, res)
    assumed = sorted(i["slug"] for i in M.m["rules"] if i["kind"] == "must" and A.classify(W)[i["slug"]] == "static")
    notes += [f"assumed, not checked (no state or call in them): {', '.join(assumed)}"] if assumed else []
    M.alloy_status = (f'checked: {len(C)} commands, {res["_ran"]} run now, the rest unchanged since they last ran' if not res["_slow"] else
                      f'{len(res["_slow"])} of {len(C)} commands took over {A.SECONDS} s (ZOOM_DIAGRAM_ALLOY_SECONDS): {", ".join(res["_slow"])}')
    M.alloy_notes += notes
    return probs


LINT = {"basis", "explained", "size", "phone", "mechanism", "paths", "depth", "naming", "media", "prose"}

RULES = [
    ("form", "the file is well formed: one root, known kinds, initial states, named edges, refs as [name](url), a valid plan", form),
    ("names", "every name is an ASCII Alloy name, clear of Alloy's keywords and the translation's words; every term is English", names),
    ("steps", "every Scenario step says what it does and expects, and follows an edge or opens or closes a level", steps),
    ("scoped", "the root and every level things enter from outside have Scenarios of their own (plan scenarios: every asks it of all); steps never climb above where they start", scoped),
    ("coverage", "every operation, rule, node, edge and trigger is used by some Scenario", coverage),
    ("basis", "no Scenario is the union of other Scenarios on its level", basis),
    ("placement", "operations sit on nodes or events, rules on nodes or edges", placement),
    ("explained", "every edge and trigger says something: a sentence, an operation or a guard", explained),
    ("size", "a level has 2 to max_nodes (7) nodes", size),
    ("phone", f"a phone can draw the root: no two of its partitions joined at more than {LIMITS['partitionLinks']} pairs of nodes", phone),
    ("mechanism", "where anything runs, root Scenarios walk an activity or state, and every component meets one of them", mechanism),
    ("partitions", "every node of a partitioned level is in one of two or more partitions, regions keep their events, crossings carry a contract (render checks the blocks)", partitions),
    ("quantities", "counts and pass-through nodes add up, flows match their stock's unit, every deadline shows what happens when it passes", quantities),
    ("paths", "a workflow or state level marks its main path, and every gate (checking, reviewing, …) shows how it fails", paths),
    ("syncs", "regions of a state level meet only through syncs: when an event, where a state, then an event in another region", syncs),
    ("depth", "an overview stops one level below the root", depth),
    ("naming", "labels follow their kind; abstract components depend only on abstract ones; marks are known", naming),
    ("media", "media sit where its type allows; an insight names a move, the usual design, the gain and a rule", media),
    ("facts", "facts state the system's facts, never the plan: no item restates the intent or lists the views", facts),
    ("prose", "a Korean model's descriptions end in -니다 or -니까, put particles by the English term's last sound with no space, write 수 있다 apart, and never point at 위/아래/앞/다음 그림", prose),
    ("unique-names", "no two things the reader sees share a name", unique_names),
    ("typed", "types are names the module declares; signatures, attributes and relations agree with the drawing", typed),
    ("vocabulary", "formulas are Alloy over the model's names, every variable bound and none hiding a name", vocabulary),
    ("balanced", "a workflow opened from a workflow shows its parent's artifacts entering and leaving", balanced),
    ("alloy", "Alloy finds the rules consistent and independent, every must rule kept, every Scenario and failure path possible", alloy),
]


def severity(name, M):
    return "lint" if name in LINT and name not in getattr(M, "strict", ()) else "error"


def run(M, prove=True, only=None):
    """(name, problems, severity) per check, in order. Alloy runs only when no error was found."""
    out = []
    M.alloy_status = "skipped: --quick" if not prove else ""
    if M.parse_problems:   # nothing else can be read until every reference resolves
        M.alloy_notes, M.alloy_status = [], "not run: fix the errors above first"
        return [("form", M.parse_problems, "error")]
    for name, _, fn in RULES:
        if only and name not in only:
            continue
        sev = severity(name, M)
        if name == "alloy":
            if not prove or any(p and s == "error" for _, p, s in out):
                M.alloy_notes = []
                M.alloy_status = M.alloy_status or "not run: fix the errors above first"
                out.append((name, [], sev))
                continue
        out.append((name, fn(M), sev))
    return out

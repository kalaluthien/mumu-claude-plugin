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
import tempfile
from pathlib import Path

from . import formula as F
from .model import MEMBER, TYPE, split_top

PRIM_SIG = {"Text", "Url", "Date"}
PRIM_INT = {"Number", "Count", "Int"}
JAR_URL = "https://github.com/AlloyTools/org.alloytools.alloy/releases/download/v6.2.0/org.alloytools.alloy.dist.jar"
JAR_SHA256 = "6b8c1cb5bc93bedfc7c61435c4e1ab6e688a242dc702a394628d9a9801edb78d"   # of the v6.2.0 jar


def ident(label):
    """UpperCamel name of a label: 'Pull request' → PullRequest, 'MCP tool' → MCPTool."""
    return "".join(w[0].upper() + w[1:] for w in re.findall(r"[A-Za-z0-9]+", label))


def lower(label):
    """lowerCamel name: 'mark ready' → markReady, 'fast-forward-push' → fastForwardPush."""
    ws = re.findall(r"[A-Za-z0-9]+", label)
    return (ws[0][0].lower() + ws[0][1:] + "".join(w[0].upper() + w[1:] for w in ws[1:])) if ws else ""


def singular(name):
    for end, cut in (("ies", "y"), ("ses", "s"), ("s", "")):
        if name.endswith(end) and not name.endswith("ss"):
            return name[: len(name) - len(end)] + cut
    return name


def artifact_types(label):
    """Type names an artifact label stands for: every tail of its words, singular or as written."""
    if re.fullmatch(r"[\w-]+\.[a-z]+", label.strip()):   # a file stands for what it holds: model.json is a Model
        label = label.rsplit(".", 1)[0]
    ws = re.findall(r"[A-Za-z0-9]+", label)
    out = set()
    for i in range(len(ws)):
        n = ident(" ".join(ws[i:]))
        out |= {n, singular(n)}
    return out


class Type:
    """A type expression: names (a union), an enum literal set, or a tuple; with a multiplicity."""

    def __init__(self, text):
        self.text = s = text.strip()
        self.mult = "one"
        for end, m in (("[1..]", "some"), ("[]", "set"), ("?", "lone")):
            if s.endswith(end):
                self.mult, s = m, s[: -len(end)].strip()
                break
        self.names, self.atoms, self.tuple = [], None, None
        if s.startswith("(") and s.endswith(")"):
            inner = s[1:-1]
            parts = split_top(inner)
            if len(parts) > 1:
                self.tuple = [Type(p) for p in parts]
                return
            s = inner.strip()
        if s.startswith("{") and s.endswith("}"):
            self.atoms = [a.strip() for a in s[1:-1].split(",") if a.strip()]
            return
        parts = [p.strip() for p in s.split("|") if p.strip()]
        if len(parts) > 1:   # a union may mark many on any member: Release | TasteNote[]
            sub = [Type(p) for p in parts]
            order = ["one", "lone", "some", "set"]
            self.mult = max([self.mult] + [t.mult for t in sub], key=order.index)
            parts = [n for t in sub for n in t.names]
        self.names = parts

    def refs(self):
        return [n for t in self.tuple for n in t.refs()] if self.tuple else list(self.names)


class World:
    """Everything the module will declare, with the name each element of the model gets in it."""

    def __init__(self, M):
        self.M, m = M, M.m
        self.problems = []
        self.sigs, self.fields, self.preds, self.atoms = {}, {}, {}, {}
        self.enums, self.kinds = {}, {}          # enum name -> atoms; call kind -> {field: decl}
        self.states, self.runs = {}, {}          # state level id -> info; workflow level id -> info
        self.var_fields, self.var_sigs = set(), set()
        self.query, self.change = {}, {}         # op slug -> info
        self.rule_name = {i["slug"]: lower(i["slug"]) for i in m["rules"]}
        self._types()
        self._components()
        self._levels()
        self._ops()
        self._events()

    def _sig(self, name, **info):
        if name in self.sigs and self.sigs[name].get("kind") != info.get("kind"):
            self.problems.append(f"{name} names both a {self.sigs[name]['kind']} and a {info['kind']}; rename one")
        self.sigs.setdefault(name, info)

    def _types(self):
        for name, txt in (self.M.m.get("types") or {}).items():
            mt = re.match(r"\s*(\{[^}]*\})", str(txt))
            if mt:
                self._enum(name, Type(mt.group(1)).atoms, f"type {name}")
            else:
                self._sig(name, kind="outside")
        for p in sorted(PRIM_SIG):
            self._sig(p, kind="primitive", used=False)

    def _enum(self, name, atoms, where):
        if name in self.enums:
            if self.enums[name] != atoms:
                self.problems.append(f"{where}: two literal sets are both called {name}; name them in types")
            return name
        for a in atoms:
            if not re.fullmatch(MEMBER, a):
                self.problems.append(f"{where}: value {a} is a lowerCamel name")
            if a in self.atoms and self.atoms[a] != name:
                self.problems.append(f"{where}: value {a} is already in {self.atoms[a]}; share one type in types")
            self.atoms[a] = name
        self.enums[name] = atoms
        self._sig(name, kind="enum")
        return name

    def type_decl(self, t, where, name_hint):
        """Alloy for a type expression, registering literal sets as enums."""
        if t.tuple:
            return " -> ".join(self.type_decl(x, where, name_hint) for x in t.tuple)
        if t.atoms is not None:
            same = [n for n, a in self.enums.items() if a == t.atoms]
            return same[0] if same else self._enum(ident(name_hint), t.atoms, where)
        u = " + ".join("Int" if n in PRIM_INT else n for n in t.names)
        return f"({u})" if len(t.names) > 1 else u

    def _components(self):
        m = self.M.m
        for L in m["levels"]:
            if L["kind"] != "topology":
                continue
            for n in L["nodes"]:
                parents = [ident(self.M.nodes[e["to"]]["label"]) for e in L["edges"]
                           if e["from"] == n["id"] and self.M.is_abstract(L, e["to"])]
                self._sig(ident(n["label"]), kind="component", node=n["id"], abstract=bool(n.get("abstract")),
                          singleton=bool(n.get("singleton")), parents=parents)
        labels = [e.get("label", "") for L in m["levels"] if L["kind"] == "workflow" for e in L["edges"] if not e.get("is")]
        labels += [f.get("edge", "") for L in m["levels"] for f in L.get("in", []) + L.get("out", [])]
        self.artifact_words = set().union(*map(artifact_types, labels))

    def use_type(self, name, where):
        if name in PRIM_INT or name == "None":
            return
        if name == "Bool":
            self.problems.append(f"{where}: Bool is only for attributes; use a literal set such as {{yes, no}} or a subset")
            return
        if name in self.sigs:
            self.sigs[name]["used"] = True
        elif name in self.artifact_words:
            self._sig(name, kind="artifact", used=True)
        else:
            self.problems.append(f"{where}: {name} is no component, artifact, enum or declared type")

    def _attrs(self):
        for L in self.M.m["levels"]:
            for n in L["nodes"]:
                for a in n.get("attrs", []):
                    ma = re.fullmatch(rf"({MEMBER})\s*:\s*(.+)", a)
                    if not ma:
                        continue
                    yield L, n, ma.group(1), Type(ma.group(2))

    def _levels(self):
        m = self.M.m
        for L, n, name, t in self._attrs():
            owner = ident(n["label"])
            if t.names == ["Bool"]:
                self._sig(ident(name), kind="subset", of=owner)
                continue
            for r in t.refs():
                self.use_type(r, f"{n['label']}.{name}")
            decl = self.type_decl(t, f"{n['label']}.{name}", name)
            self.fields.setdefault(name, []).append({"owner": owner, "mult": t.mult if not t.tuple else "set", "decl": decl, "type": t})
        for L in m["levels"]:   # a relation no attribute stands for is a field named by its verb
            if L["kind"] != "topology":
                continue
            for e in L["edges"]:
                if self.M.is_abstract(L, e["to"]) or e.get("attr"):
                    continue
                owner, to = ident(self.M.nodes[e["from"]]["label"]), ident(self.M.nodes[e["to"]]["label"])
                if any(f["owner"] == owner and to in (f["type"].refs() if f.get("type") else []) for fs in self.fields.values() for f in fs):
                    continue
                fs = self.fields.setdefault(lower(e["label"]), [])
                same = next((f for f in fs if f["owner"] == owner and f.get("relation")), None)
                if same:   # one verb from one component to several: one field over their union
                    same["decl"] += " + " + to
                    same["type"] = Type(" | ".join(t + "[]" for t in same["decl"].split(" + ")))
                else:
                    fs.append({"owner": owner, "mult": "set", "decl": to, "type": Type(to + "[]"), "relation": e["label"]})
        for L in m["levels"]:
            if L["kind"] == "state":
                subj = L.get("subject")
                if not subj:
                    self.problems.append(f'{L["id"]}: name the subject, the thing whose states these are')
                    continue
                self.use_type(subj, f'{L["id"]} subject')
                region = {n["id"]: n.get("partition") or "_" for n in L["nodes"]}
                for n in L["nodes"]:
                    self._sig(ident(n["label"]), kind="state", of=subj, level=L["id"])
                    self.var_sigs.add(ident(n["label"]))
                self.states[L["id"]] = {"subject": subj, "region": region}
            elif L["kind"] == "workflow":
                run_sig = ident(L["title"])
                self._sig(run_sig, kind="run", level=L["id"], used=True)
                steps = [ident(n["label"]) for n in L["nodes"]]
                for s_ in steps:
                    self.atoms[s_] = run_sig + "Step"
                self.enums[run_sig + "Step"] = steps
                self._sig(run_sig + "Step", kind="enum")
                self.runs[L["id"]] = {"run": run_sig, "steps": steps}

    def _ops(self):
        sits = self.M.sits()
        moving = {lid for lid in self.states} | {lid for lid in self.runs}
        for o in self.M.m["operations"]:
            sl = o["slug"]
            if sl not in self.M.sigs:
                continue
            rcv, verb = sl.split(".")
            ms = re.fullmatch(r"\s*\((.*)\)\s*→\s*(.+)", o["sig"])
            params = []
            for p in split_top(ms.group(1)):
                if ":" not in p:
                    continue
                pn, pt = p.split(":", 1)
                t = Type(pt)
                for r in t.refs():
                    self.use_type(r, sl)
                params.append((pn.strip(), t, self.type_decl(t, sl, pn.strip())))
            res = Type(ms.group(2))
            for r in res.refs():
                self.use_type(r, sl)
            self.use_type(rcv, sl)
            rdecl = None if res.names == ["None"] else self.type_decl(res, sl, verb + "Result")
            on = sits.get(sl, set())
            placed_moving = any((k == "node" and self.M.node_level[x] in moving) or k in ("edge", "trig") for k, x in on)
            info = {"slug": sl, "receiver": rcv, "verb": verb, "params": params, "result": res, "rdecl": rdecl,
                    "pre": o.get("pre"), "post": o.get("post"), "modifies": o.get("modifies", [])}
            if o.get("modifies") or placed_moving:
                kind = rcv + verb[0].upper() + verb[1:]
                info["kind"] = kind
                fields = {"self": f"one {rcv}"}
                for pn, t, d in params:
                    fields[pn] = f"{self._mult(t)} {d}"
                if rdecl:
                    fields["result"] = f"{self._mult(res)} {rdecl}"
                self.kinds[kind] = fields
                self.change[sl] = info
                self._pred(verb, [rcv] + [d for _, _, d in params] + ([rdecl] if rdecl else []), sl)
                self._pred(verb, [rcv], sl)
            else:
                self.query[sl] = info
                arrow = " -> ".join([d for _, _, d in params] + [f"{self._mult(res)} {rdecl or 'univ'}"]) if params else f"{self._mult(res)} {rdecl or 'univ'}"
                self.fields.setdefault(verb, []).append({"owner": rcv, "mult": "query", "decl": arrow, "op": sl})
            for x in o.get("modifies", []):
                mm = re.fullmatch(rf"({TYPE})\.({MEMBER})", x)
                ok = mm and (any(f["owner"] == mm.group(1) and f["mult"] != "query" for f in self.fields.get(mm.group(2), []))
                             or self.sigs.get(ident(mm.group(2)), {}).get("of") == mm.group(1))
                if not ok:
                    self.problems.append(f"{sl}: modifies {x}, which is no Type.attribute")
                    continue
                self.var_fields.add((mm.group(1), mm.group(2)))
                if self.sigs.get(ident(mm.group(2)), {}).get("kind") == "subset":
                    self.var_sigs.add(ident(mm.group(2)))

    @staticmethod
    def _mult(t):
        return "set" if t.tuple else t.mult

    def _pred(self, name, types, where):
        sig = tuple(types)
        have = self.preds.setdefault(name, [])
        if any(h["types"] == sig and h["where"] != where for h in have):
            self.problems.append(f"{where}: {name}{list(sig)} is declared twice; rename one")
        if not any(h["types"] == sig for h in have):
            have.append({"types": sig, "where": where})

    def _events(self):
        self.edge_kind = {}       # edge key -> call kind
        self.event_pred = {}      # (level id, label) -> pred name
        m = self.M
        for lid, info in self.states.items():
            L, subj = m.levels[lid], info["subject"]
            for k, (LL, e) in m.edges.items():
                if LL["id"] != lid:
                    continue
                ops = [x for x in e.get("ops", []) if x in self.change]
                if len(e.get("ops", [])) > 1:
                    self.problems.append(f'{lid}: event {e["label"]} carries one operation, not {len(e["ops"])}')
                if ops:
                    op = self.change[ops[0]]
                    if op["receiver"] != subj:
                        self.problems.append(f'{lid}: event {e["label"]} calls {ops[0]}, but the subject is {subj}')
                    kind, name = op["kind"], (op["verb"] if lower(e["label"]) == op["verb"] else lower(e["label"]))
                else:
                    kind, name = subj + ident(e["label"]), lower(e["label"])
                    self.kinds.setdefault(kind, {"self": f"one {subj}"})
                self.edge_kind[k] = kind
                self.event_pred[(lid, e["label"])] = name
                if not ops or name != self.change[ops[0]]["verb"]:
                    self._pred(name, [subj], f'{lid}: {e["label"]}')
            for t in L.get("triggers", []):
                ops = [x for x in t.get("ops", []) if x in self.change]
                if ops:
                    op = self.change[ops[0]]
                    kind, name = op["kind"], (op["verb"] if lower(t["label"]) == op["verb"] else lower(t["label"]))
                else:
                    kind, name = subj + ident(t["label"]), lower(t["label"])
                    self.kinds.setdefault(kind, {"self": f"one {subj}"})
                self.edge_kind[("trig", lid, t["label"])] = kind
                self.event_pred[(lid, t["label"])] = name
                if not ops or name != self.change[ops[0]]["verb"]:
                    self._pred(name, [subj], f'{lid}: {t["label"]}')
        for lid, info in self.runs.items():
            L, run_sig = m.levels[lid], info["run"]
            node_ops = {n["id"]: [x for x in n.get("ops", []) if x in self.change] for n in L["nodes"]}

            def producer(node_id, label):
                for x in node_ops.get(node_id, []):
                    if set(self.change[x]["result"].refs()) & artifact_types(label):
                        return self.change[x]["kind"]
                return None

            for k, (LL, e) in m.edges.items():
                if LL["id"] != lid:
                    continue
                kind = producer(e["from"], e["label"]) or run_sig + ident(e["label"])
                self.kinds.setdefault(kind, {})
                self.edge_kind[k] = kind
                self.event_pred[(lid, e["label"])] = lower(e["label"])
                if lower(e["label"]) not in self.preds:
                    self._pred(lower(e["label"]), [], f'{lid}: {e["label"]}')
            for t in L.get("triggers", []):
                kind = run_sig + ident(t["label"])
                self.kinds.setdefault(kind, {})
                self.edge_kind[("trig", lid, t["label"])] = kind
                self.event_pred[(lid, t["label"])] = lower(t["label"])
                self._pred(lower(t["label"]), [], f'{lid}: {t["label"]}')
            for f in L.get("in", []):
                kind = run_sig + "In" + ident(f["edge"])
                self.kinds.setdefault(kind, {})
                self.edge_kind[("in", lid, f["edge"])] = kind
            for f in L.get("out", []):
                for fr in [f["from"]] if isinstance(f.get("from"), str) else f.get("from", []):
                    kind = producer(fr, f["edge"]) or run_sig + "Out" + ident(f["edge"])
                    self.kinds.setdefault(kind, {})
                    self.edge_kind[("out", lid, f["edge"], fr)] = kind
        for rule, name in self.rule_name.items():
            self._pred(name, [], f"rule {rule}")

    def scope(self):
        free = set(self.sigs) | set(self.atoms) | set(self.fields) | set(self.preds) | {"at"}
        member = set(self.fields) | set(self.preds) | {"at"}
        return free, member

    def check_formula(self, text, where, extra=()):
        """Problems with one formula: it parses, and every name is bound or a word of the module."""
        try:
            us = F.uses(text)
        except F.FormulaError as e:
            return [f"{where}: {e}"]
        free, member = self.scope()
        free |= set(extra)
        out = set()
        try:
            out |= {f"variable {v} hides the {'attribute' if v in self.fields else 'name'} {v}; rename the variable"
                    for v in F.binders(text) if v in self.fields or v in self.sigs or v in self.preds or v in self.atoms}
        except F.FormulaError:
            pass
        for kind, name, _, bound in us:
            if name in bound:
                continue
            if kind == "member" and name not in member and name not in free:
                out.add(f".{name} is no attribute or operation")
            elif kind in ("free", "call") and name not in free:
                guess = [s for s in self.sigs if s.lower() == name.lower() or singular(s) == name]
                out.add(f"{name} is unbound" + (f" (did you mean {guess[0]}?)" if guess else ""))
        return [f"{where}: " + "; ".join(sorted(out))] if out else []

    def dynamic(self, text, seen=()):
        """Whether a formula speaks of something that changes: a state, a var field, a call, a step, or time."""
        try:
            us = F.uses(text)
            if F.temporal(text):
                return True
        except F.FormulaError:
            return False
        varf = {f for _, f in self.var_fields}
        calls = {n for n, hs in self.preds.items() if any(h["where"] not in [f"rule {i}" for i in self.rule_name] for h in hs)}
        rule_by = {v: k for k, v in self.rule_name.items()}
        fields = {n for n, fs in self.fields.items() if any(f["mult"] != "query" for f in fs)}
        for kind, name, _, bound in us:
            if name in bound:
                continue
            as_call = kind == "call" or (name in calls and not (kind == "member" and name in fields))
            if name in self.var_sigs or name in varf or name == "at" or as_call:
                return True
            if name in rule_by and name not in seen and self.dynamic(self.M.rules[rule_by[name]]["formula"], seen + (name,)):
                return True
        return False


def classify(W):
    """rule slug -> 'guard' (behaviour, always), 'dynamic' (checked) or 'static' (assumed or ideal)."""
    M, out = W.M, {}
    sits = M.sits()
    for i in M.m["rules"]:
        on = sits.get(i["slug"], set())
        guard = i["kind"] == "must" and any((k == "edge" and M.edges[x][0]["kind"] != "topology") or k == "trig" for k, x in on)
        out[i["slug"]] = "guard" if guard else ("dynamic" if W.dynamic(i["formula"]) else "static")
    return out


def translate(M):
    W = World(M)
    m, cls = M.m, classify(W)
    slug = re.sub(r"[^A-Za-z0-9]", "_", m.get("title", "model"))
    L_ = [f"module {slug}", f"-- {m.get('title', '')}: generated by zoom from the Schema; edit the model, not this file.", ""]

    L_.append("-- things")
    for name, s in W.sigs.items():
        if s["kind"] in ("primitive", "artifact", "outside") and s.get("used", True):
            L_.append(f"sig {name} {{}}")
    for name, atoms in W.enums.items():
        L_.append(f"enum {name} {{ {', '.join(atoms)} }}")
    comps = [(n, s) for n, s in W.sigs.items() if s["kind"] == "component"]
    order = sorted(comps, key=lambda x: (len(x[1]["parents"]) > 0, x[0]))
    # a query is a relation of one arity more than its parameters, and Kodkod refuses one over a few hundred atoms
    # beyond arity 3 ("translation capacity exceeded"): declare a query only where a formula of the module names it
    said = [i["formula"] for i in m["rules"]] + [L["init"] for L in M.levels.values() if L.get("init")]
    said += [x for op in W.change.values() for x in (op.get("pre"), op.get("post")) if x]
    named = set()
    for text in said:
        try:
            named |= {name for _, name, _, _ in F.uses(text)}
        except F.FormulaError:
            pass
    for name, s in order:
        fields = []
        for fname, fs in W.fields.items():
            for f in fs:
                if f["owner"] != name or (f["mult"] == "query" and fname not in named):
                    continue
                var = "var " if (name, fname) in W.var_fields else ""
                mult = "" if f["mult"] == "query" else ("set " if f["mult"] == "set" and "->" in f["decl"] else f["mult"] + " ")
                fields.append(f"{var}{fname}: {mult}{f['decl']}")
        head = ("abstract " if s["abstract"] else "") + ("one " if s["singleton"] else "") + f"sig {name}"
        ps = s["parents"]
        if len(ps) == 1:
            head += f" extends {ps[0]}"
        elif len(ps) > 1:
            head += " in " + " + ".join(ps)
        L_.append(head + (" {\n  " + ",\n  ".join(fields) + "\n}" if fields else " {}"))
    for name, s in W.sigs.items():
        if s["kind"] == "subset":
            L_.append(f"{'var ' if name in W.var_sigs else ''}sig {name} in {s['of']} {{}}")
    for lid, info in W.states.items():
        regions = {}
        for n in M.levels[lid]["nodes"]:
            regions.setdefault(info["region"][n["id"]], []).append(ident(n["label"]))
        for r, sts in regions.items():
            L_.append(f"var sig {', '.join(sts)} in {info['subject']} {{}}")
    for lid, info in W.runs.items():
        L_.append(f"one sig {info['run']} {{ var at: set {info['run']}Step }}")

    L_ += ["", "-- calls: each step of a run is the set of calls made in it", "abstract sig Call {}", "one sig Now { var happens: set Call }"]
    for kind, fields in W.kinds.items():   # a call with no arguments is one atom; others get one per argument list
        body = ", ".join(f"{k}: {v}" for k, v in fields.items())
        L_.append(f"{'' if body else 'one '}sig {kind} extends Call {{{' ' + body + ' ' if body else ''}}}")
    L_.append("pred stutter { no Now.happens }")

    L_ += ["", "-- what happened in this step"]
    for sl, op in W.change.items():
        ps = [("s", op["receiver"])] + [(pn + "_", f"{W._mult(t)} {d}") for pn, t, d in op["params"]] + ([("result_", f"{W._mult(op['result'])} {op['rdecl']}")] if op["rdecl"] else [])
        eq = " and ".join(["c.self = s"] + [f"c.{pn} = {pn}_" for pn, _, _ in op["params"]] + (["c.result = result_"] if op["rdecl"] else []))
        decl = ", ".join(f"{a}: {b}" for a, b in ps)
        L_.append(f"pred {op['verb']}[{decl}] {{ some c: Now.happens & {op['kind']} | {eq} }}")
        L_.append(f"pred {op['verb']}[s: {op['receiver']}] {{ some c: Now.happens & {op['kind']} | c.self = s }}")
    done = {(op["verb"], op["receiver"]) for op in W.change.values()}
    for lid, info in W.states.items():
        subj, labels = info["subject"], {}
        for k, (LL, e) in M.edges.items():
            if LL["id"] == lid:
                labels.setdefault(e["label"], []).append((k, e))
        for lab, es in labels.items():
            name = W.event_pred[(lid, lab)]
            if (name, subj) in done:
                continue
            done.add((name, subj))
            kind = W.edge_kind[es[0][0]]
            froms = " + ".join(sorted({ident(M.nodes[e["from"]]["label"]) for _, e in es}))
            L_.append(f"pred {name}[s: {subj}] {{ some c: Now.happens & {kind} | c.self = s and s in {froms} }}")
        for t in M.levels[lid].get("triggers", []):
            name = W.event_pred[(lid, t["label"])]
            if (name, subj) not in done:
                done.add((name, subj))
                L_.append(f"pred {name}[s: {subj}] {{ some c: Now.happens & {W.edge_kind[('trig', lid, t['label'])]} | c.self = s }}")
    for lid, info in W.runs.items():
        for t in M.levels[lid].get("triggers", []):
            L_.append(f"pred {lower(t['label'])} {{ some Now.happens & {W.edge_kind[('trig', lid, t['label'])]} }}")
        handed = {}
        for k, (LL, e) in M.edges.items():   # an artifact is handed on when its producer runs in the active step
            if LL["id"] == lid:
                handed.setdefault(lower(e["label"]), []).append(f"(some Now.happens & {W.edge_kind[k]} and {ident(M.nodes[e['from']]['label'])} in {info['run']}.at)")
        for name, ways in handed.items():
            L_.append(f"pred {name} {{ {' or '.join(ways)} }}")

    L_ += ["", "-- rules"]
    for i in m["rules"]:
        L_.append(f"-- {i['slug']} ({i['kind']}, {cls[i['slug']]})")
        L_.append(f"pred {W.rule_name[i['slug']]} {{\n  " + F.layout(i["formula"]).replace("\n", "\n  ") + "\n}")

    def superstate(lid):
        """The state a state level is opened from, whose instances its states partition, or None."""
        p = M.levels[lid].get("parent")
        # a level of another subject only zooms in, since its instances are not the superstate's
        same = p and M.node_level[p] in W.states and W.states[M.node_level[p]]["subject"] == W.states[lid]["subject"]
        return ident(M.nodes[p]["label"]) if same else None

    def resumed(lid):
        """When entering its superstate resumes a level, as a conjunct to add: always ("") by its own history, else
        when a deep history above it is entered in the same step; None when never."""
        if M.levels[lid].get("history"):
            return ""
        conds, a = [], M.node_level[M.levels[lid]["parent"]]
        while superstate(a):
            if M.levels[a].get("history") == "deep":
                conds.append(f"(s not in {superstate(a)} and s in {superstate(a)}')")
            a = M.node_level[M.levels[a]["parent"]]
        return f" and ({' or '.join(conds)})" if conds else None

    B = []
    for lid, info in W.states.items():
        L, subj = M.levels[lid], info["subject"]
        regions = {}
        for n in L["nodes"]:
            regions.setdefault(info["region"][n["id"]], []).append(n)
        inits = [L["initial"]] if isinstance(L.get("initial"), str) else L.get("initial") or []
        up = superstate(lid)
        again = resumed(lid) if up else None
        B.append(f"-- {L['title']}" + (f", inside {up}" if up else ""))
        B.append(f"all s: {up or subj} | " + " and ".join(f"s in {ident(M.nodes[i]['label'])}" for i in inits))
        for r, ns in regions.items():
            sts = [ident(n["label"]) for n in ns]
            B.append(f"always ({up or subj} = {' + '.join(sts)}" + "".join(f" and no {a} & {b}" for x, a in enumerate(sts) for b in sts[x + 1:]) + ")")
            if up:   # entering the superstate enters each region at its initial state, or where history left it
                init = next(ident(M.nodes[i]["label"]) for i in inits if info["region"][i] == r)
                enter = f"s not in {up} and s in {up}'"
                held = f" and not (once (s in {' + '.join(sts)}){again})" if again is not None else ""
                B.append(f"always (all s: {subj} | ({enter}{held}) implies s in {init}')")
                if again is not None:
                    B += [f"always (all s: {subj} | ({enter}{again} and ((s not in {up}) since (s in {x}))) implies s in {x}')" for x in sts]
            pairs = {}
            for k, (LL, e) in M.edges.items():
                if LL["id"] == lid and e["from"] in {n["id"] for n in ns}:
                    pairs.setdefault((W.edge_kind[k], ident(M.nodes[e["from"]]["label"])), set()).add(ident(M.nodes[e["to"]]["label"]))
            for (kind, frm), tos in pairs.items():   # leaving the superstate in the same step cuts the event short
                B.append(f"always (all c: Now.happens & {kind} | c.self in {frm}{f' and after c.self in {up}' if up else ''} implies after c.self in {' + '.join(sorted(tos))})")
            enable = {}
            for (kind, frm) in pairs:
                enable.setdefault(kind, []).append(frm)
            for kind, frms in enable.items():   # an event happens only in a state that handles it
                B.append(f"always (all c: Now.happens & {kind} | c.self in {' + '.join(sorted(frms))})")
            trig = [(W.edge_kind[("trig", lid, t["label"])], ident(M.nodes[t["to"]]["label"])) for t in L.get("triggers", []) if info["region"][t["to"]] == r]
            for kind, to in trig:
                B.append(f"always (all c: Now.happens & {kind} | after c.self in {to})")
            moves = [f"(s in {frm} and some c: Now.happens & {kind} | c.self = s)" for (kind, frm) in pairs] + [f"(some c: Now.happens & {kind} | c.self = s)" for kind, _ in trig]
            moves += [f"(s not in {up} and s in {up}')", f"(s in {up} and s not in {up}')"] if up else []
            same = " and ".join(f"(s in {x} iff s in {x}')" for x in sts)
            B.append(f"always (all s: {subj} | ({same})" + "".join(f"\n    or {mv}" for mv in moves) + ")")
        for y in L.get("syncs", []):
            when, then = W.event_pred[(lid, y["when"])], W.event_pred[(lid, y["then"])]
            where = f" and s in {ident(M.nodes[y['where']]['label'])}" if y.get("where") else ""
            B.append(f"always (all s: {subj} | (s.{when}{where}) implies s.{then})   -- sync {y['name']}")
    for lid, info in W.runs.items():
        L, run_sig = M.levels[lid], info["run"]
        B.append(f"-- {L['title']}")
        opened = L.get("triggers") or L.get("in")   # a run opened from outside starts empty; otherwise at its first steps
        firsts = [ident(n["label"]) for n in L["nodes"] if not any(e["to"] == n["id"] and e["from"] != n["id"] for e in L["edges"])]
        B.append(f"no {run_sig}.at" if opened or not firsts else f"{run_sig}.at = {' + '.join(firsts)}")
        ent, lea = {}, {}
        pairs = {}
        for k, (LL, e) in M.edges.items():
            if LL["id"] != lid:
                continue
            frm, to = ident(M.nodes[e["from"]]["label"]), ident(M.nodes[e["to"]]["label"])
            pairs.setdefault((W.edge_kind[k], frm), set()).add(to)
        for f in L.get("out", []):
            for fr in [f["from"]] if isinstance(f.get("from"), str) else f.get("from", []):
                pairs.setdefault((W.edge_kind[("out", lid, f["edge"], fr)], ident(M.nodes[fr]["label"])), set())
        starts = [(W.edge_kind[("trig", lid, t["label"])], ident(M.nodes[t["to"]]["label"])) for t in L.get("triggers", [])]
        starts += [(W.edge_kind[("in", lid, f["edge"])], ident(M.nodes[f["to"]]["label"])) for f in L.get("in", [])]
        for (kind, frm), tos in pairs.items():
            stay = frm in tos
            eff = (f"some ({' + '.join(sorted(tos))}) & {run_sig}.at'" if tos else "") + ("" if stay else (" and " if tos else "") + f"{frm} not in {run_sig}.at'")
            B.append(f"always ((some Now.happens & {kind} and {frm} in {run_sig}.at) implies {eff})")
            for t in tos:
                ent.setdefault(t, []).append(f"(some Now.happens & {kind} and {frm} in {run_sig}.at)")
            lea.setdefault(frm, []).append(f"(some Now.happens & {kind} and {frm} in {run_sig}.at)")
        for kind, to in starts:
            B.append(f"always (some Now.happens & {kind} implies {to} in {run_sig}.at')")
            ent.setdefault(to, []).append(f"some Now.happens & {kind}")
        for st in info["steps"]:
            e_ = " or ".join(ent.get(st, [])) or "some none"
            l_ = " or ".join(lea.get(st, [])) or "some none"
            B.append(f"always ({st} not in {run_sig}.at and {st} in {run_sig}.at' implies ({e_}))")
            B.append(f"always ({st} in {run_sig}.at and {st} not in {run_sig}.at' implies ({l_}))")
    B.append("-- operations")
    for lid, info in W.states.items():   # an operation drawn on a state runs only while its subject is there
        for n in M.levels[lid]["nodes"]:
            for x in n.get("ops", []):
                op = W.change.get(x)
                if not op:
                    continue
                arg = "self" if op["receiver"] == info["subject"] else next((pn for pn, t, _ in op["params"] if t.names == [info["subject"]]), None)
                if arg:
                    B.append(f"always (all c: Now.happens & {op['kind']} | c.{arg} in {ident(n['label'])})")
    for sl, op in W.change.items():
        mp = {"self": "c.self", "result": "c.result"} | {pn: "c." + pn for pn, _, _ in op["params"]}
        conds = [F.rename(x, mp) for x in (op.get("pre"), op.get("post")) if x]
        if conds:
            B.append(f"always (all c: Now.happens & {op['kind']} | " + " and ".join(f"({x})" for x in conds) + ")")
    for owner, field in sorted(W.var_fields):
        kinds = sorted({op["kind"] for op in W.change.values() if f"{owner}.{field}" in op["modifies"]})
        if not kinds:
            continue
        mods = [op for op in W.change.values() if f"{owner}.{field}" in op["modifies"]]
        by = " or ".join(f"(some c: Now.happens & {op['kind']} | c.self = x)" if op["receiver"] == owner else f"some Now.happens & {op['kind']}"
                         for op in sorted(mods, key=lambda o: o["kind"]))
        S = ident(field)
        if W.sigs.get(S, {}).get("kind") == "subset" and W.sigs[S]["of"] == owner:
            B.append(f"always (all x: {owner} | (x in {S} iff x in {S}') or {by})")
        else:
            B.append(f"always (all x: {owner} | x.{field}' = x.{field} or {by})")
    for i in m["rules"]:
        if cls[i["slug"]] == "guard":
            B.append(f"always {W.rule_name[i['slug']]}   -- guard")
    for lid in M.levels:
        if M.levels[lid].get("init"):
            B.append(f"{M.levels[lid]['init']}   -- init of {lid}")
    L_ += ["", "-- how things move", "pred behaviour {\n  " + "\n  ".join(B) + "\n}"]

    musts_static = [W.rule_name[i["slug"]] for i in m["rules"] if cls[i["slug"]] == "static" and i["kind"] == "must"]

    C = []
    for i in m["rules"]:   # every rule is asked, a static one under the others, so none is assumed to prove itself
        me = W.rule_name[i["slug"]]
        given = " and ".join([x for x in musts_static if x != me] + ["behaviour"])
        C.append((f"holds_{me}", "check", f"{given} implies always {me}", 0 if i["kind"] == "must" else None, i["slug"]))
    L_ += ["", "-- what Alloy checks"]
    scopes = {i["slug"]: i["scope"] for i in m["rules"] if i.get("scope")}
    for name, _, body, exp, slug in C:
        calls = len(W.kinds) + 3   # room for every kind of call at least once, and a few repeats
        more = f", {scopes[slug]}" if slug in scopes else ""
        L_.append(f"check {name} {{ {body} }} for 3 but {calls} Call, 8 steps{more}" + (f" expect {exp}" if exp is not None else ""))
    return "\n".join(L_) + "\n", W, C


def jar():
    for p in (os.environ.get("ALLOY_JAR"), Path.home() / ".cache/paperwork-alloy/alloy.jar"):
        if p and Path(p).is_file():
            return str(p)
    return None


def ready():
    """Whether Alloy can run here: a jar and a `java` to run it."""
    return bool(jar() and shutil.which("java"))


def fetch():
    dest = Path.home() / ".cache/paperwork-alloy/alloy.jar"
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-sSL", "-o", str(dest), JAR_URL], check=True)
    import hashlib
    if hashlib.sha256(dest.read_bytes()).hexdigest() != JAR_SHA256:
        dest.unlink()
        raise SystemExit(f"alloy.jar is not the pinned {JAR_URL}; deleted")
    return str(dest)


CACHE = Path.home() / ".cache/paperwork-alloy/results"
SECONDS = int(os.environ.get("PAPERWORK_ALLOY_SECONDS", "120"))
JVMS = min(os.cpu_count() or 1, 4)


def _split(text):
    """The module above the commands, the commands, and the key and name of a command."""
    import hashlib
    i = text.index("-- what Alloy checks")
    head, cmds = text[:i], [c for c in text[i:].splitlines()[1:] if c.strip()]
    key = lambda c: hashlib.sha256((head + "\n" + c).encode()).hexdigest()
    name_of = lambda c: re.match(r"\s*(?:run|check)\s+(\w+)", c).group(1)
    return head, cmds, key, name_of


def _stored(text):
    """The stored answer of every command whose text (with the module above it) was answered before; one that ran
    out of time stays unanswered unless given more time now."""
    head, cmds, key, name_of = _split(text)
    stored = {c: json.loads((CACHE / key(c)).read_text()) for c in cmds if (CACHE / key(c)).exists()}
    return {c: r for c, r in stored.items() if r.get("slow", SECONDS) >= SECONDS}


def _result(text, stored):
    import hashlib
    head, cmds, key, name_of = _split(text)
    warn_file = CACHE / (hashlib.sha256(head.encode()).hexdigest() + ".warnings")
    warn = json.loads(warn_file.read_text()) if warn_file.exists() else []
    res = {name_of(c): r for c, r in stored.items() if "slow" not in r}
    return res, warn, [name_of(c) for c, r in stored.items() if "slow" in r]


def cached(text):
    """Alloy's stored answers for a module, without starting Alloy: {name: {sat, instances}, _warnings, _ran, _slow}."""
    if not CACHE.is_dir():
        return {"_warnings": [], "_ran": 0, "_slow": []}
    res, warn, slow = _result(text, _stored(text))
    res["_warnings"], res["_ran"], res["_slow"] = warn, 0, slow
    return res


def run(text):
    """Run each command whose text (with the module above it) is new, one process per command, at most JVMS at
    once, with Glucose and at most SECONDS each; reuse the stored answer of every other. A command that runs out
    of time is left unanswered and listed in _slow. Returns {name: {sat, instances}, _warnings, _ran, _slow}, or
    None where Alloy cannot run."""
    import hashlib
    from concurrent.futures import ThreadPoolExecutor
    if not ready():
        return None
    j = jar()
    head, cmds, key, name_of = _split(text)
    CACHE.mkdir(parents=True, exist_ok=True)
    stored = _stored(text)
    todo = [c for c in cmds if c not in stored]
    warn_file = CACHE / (hashlib.sha256(head.encode()).hexdigest() + ".warnings")
    res, warn, slow = _result(text, stored)
    work = tempfile.mkdtemp(prefix="paperwork-alloy-")   # private to this run: two checks at once never share a file

    def one(k, c):
        part, out = Path(work) / f"c{k}.als", Path(work) / f"o{k}"
        part.write_text(head + "-- what Alloy checks\n" + c + "\n")
        try:
            p = subprocess.run(["java", "-jar", j, "exec", "-f", "-s", "glucose", "-o", str(out), str(part)],
                               capture_output=True, text=True, timeout=SECONDS)
        except subprocess.TimeoutExpired:
            return c, None, None, ""
        return c, p.stdout + p.stderr, out / "receipt.json", part.read_text()

    try:
        with ThreadPoolExecutor(JVMS) as pool:
            for c, log, rec, module in pool.map(lambda kc: one(*kc), enumerate(todo)):
                if log is None:
                    slow.append(name_of(c))
                    (CACHE / key(c)).write_text(json.dumps({"slow": SECONDS}))
                    continue
                if not rec.exists():
                    msg = [l for l in log.splitlines() if ("error" in l.lower() or "line" in l or "capacity" in l or "cannot be" in l) and "JAVA_TOOL" not in l and not l.strip().startswith("at ")]
                    raise RuntimeError("\n".join(msg[:6]) or "no receipt from Alloy")
                if c == todo[0]:   # type warnings belong to the module, so one command's log has them all
                    warn = warnings(log, module)
                for name, r in json.loads(rec.read_text())["commands"].items():
                    sols = r.get("solution") or []
                    sat = bool(sols and sols[0].get("instances"))
                    res[name] = {"sat": sat, "instances": sols[0].get("instances") if sat else None}
                    (CACHE / key(c)).write_text(json.dumps(res[name]))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if todo:
        warn_file.write_text(json.dumps(warn))
    res["_warnings"], res["_ran"], res["_slow"] = warn, len([c for c in todo if name_of(c) not in slow]), slow
    return res


def warnings(text, module):
    """Alloy's type warnings, each as the line of the module it points at and Alloy's reason."""
    src = module.splitlines()
    out = []
    for m in re.finditer(r"line (\d+), column \d+.*?\n(.+?)(?:\n(?:Left|Right) type|\n\s*\d+\. |\Z)", text, re.S):
        line = src[int(m.group(1)) - 1].strip() if int(m.group(1)) <= len(src) else ""
        reason = " ".join(m.group(2).split())
        if "unused" in reason:
            continue
        out.append(f"{reason} — in: {line[:120]}")
    return out


def calls_in(instances, W=None):
    """The calls made at each step of a run, named as the model names them (an operation, event or trigger)."""
    names = {}
    if W:
        for op in W.change.values():
            names[op["kind"]] = op["slug"]
        for k, kind in W.edge_kind.items():
            if kind not in names:
                names[kind] = W.M.edges[k][1]["label"] if k in W.M.edges else k[2] if isinstance(k, tuple) else kind
    steps = []
    for inst in instances or []:
        now = next((v for k, v in inst["values"].items() if k.startswith("Now$")), {})
        steps.append(sorted({names.get(re.sub(r"\$\d+$", "", c[0]), re.sub(r"\$\d+$", "", c[0])) for c in now.get("happens", [])}))
    return steps


def sit_ids(M, slug):
    """The ids of the nodes and edges an operation or rule sits on, a trigger standing for the node it enters."""
    return {M.trigs[x][1]["to"] if k == "trig" else x for k, x in M.sits().get(slug, ())}


def element_ids(W):
    """Each call kind and each signature, as the ids of the Schema nodes and edges they stand for."""
    M, kinds = W.M, {}
    for k, kind in W.edge_kind.items():
        if isinstance(k, str):
            ids = {k}
        else:
            L = M.levels[k[1]]
            ids = ({t["to"] for t in L.get("triggers", []) if t["label"] == k[2]} if k[0] == "trig"
                   else {f["to"] for f in L.get("in", []) if f["edge"] == k[2]} if k[0] == "in" else {k[3]})
        kinds.setdefault(kind, set()).update(ids)
    for op in W.change.values():   # a call drawn as an edge is that edge; another is where its operation sits
        if op["kind"] not in kinds:
            kinds[op["kind"]] = sit_ids(M, op["slug"])
    sigs = {}
    for n in M.nodes.values():
        sigs.setdefault(ident(n["label"]), n["id"])
    return kinds, sigs


def trace(W, instances, slug):
    """A counterexample as Schema ids: the nodes whose things witness it, in brackets, then the elements called at
    each step, ` + ` within a step and `|` between elements one call may stand for; where it names neither, the
    nodes and edges the rule sits on."""
    kinds, sigs = element_ids(W)
    atom = lambda a: re.sub(r"\$\d+$", "", a)

    def node_of(sig, seen=()):
        if sig in sigs:
            return sigs[sig]
        for p in W.sigs.get(sig, {}).get("parents", []):
            if p not in seen and (n := node_of(p, seen + (sig,))):
                return n
        return None

    witness = sorted({n for sk in (instances[0].get("skolems") or {}).values() for row in sk.get("data", [])
                      for a in row if (n := node_of(atom(a)))}) if instances else []
    steps = []
    for inst in instances or []:
        now = next((v for k, v in inst["values"].items() if k.startswith("Now$")), {})
        step = sorted({"|".join(sorted(kinds.get(atom(c[0]), ()))) for c in now.get("happens", [])} - {""})
        if step:
            steps.append(" + ".join(step))
    parts = ([f"[{', '.join(witness)}]"] if witness else []) + ([" → ".join(steps)] if steps else [])
    return " ".join(parts) or ", ".join(sorted(sit_ids(W.M, slug)))


def story(steps):
    """A run as one line: the calls of each step, in order; empty steps are dropped."""
    return " → ".join(" + ".join(s) for s in steps if s) or "no call at all"


def solve(M):
    """The module's names, its commands and Alloy's answers (None without Alloy); unchanged commands are not rerun."""
    als, W, C = translate(M)
    return W, C, run(als)


def stored(M):
    """The same, from the stored answers only: Alloy is never started."""
    als, W, C = translate(M)
    return W, C, cached(als)


def standing(M, W, res):
    """Each rule's standing for the page: guard, assumed, ideal, holds or not checked, and the run that breaks it."""
    cls, out = classify(W), {}
    for i in M.m["rules"]:
        c = cls[i["slug"]]
        r = (res or {}).get(f"holds_{W.rule_name[i['slug']]}")
        role = {"guard": "guard", "static": "assumed" if i["kind"] == "must" else "ideal"}.get(c) or ("holds" if r else "not checked")
        out[i["slug"]] = (role, [s for s in calls_in(r["instances"], W) if s] if r and r["sat"] else None)
    return out


def verdicts(M, W, C, res):
    """Notes (Alloy's type warnings, a should rule that can break) and findings (a must rule the behaviour can
    break: a defect of the system, reported, never fixed by bending the model)."""
    notes, findings = [f"Alloy warns: {w}" for w in res.get("_warnings", [])], []
    for name, _, _, exp, what in C:
        r = res.get(name)
        if r and r["sat"]:
            (findings if exp == 0 else notes).append(f"{what}: can break in this run: {story(calls_in(r['instances'], W))}")
    return notes, findings

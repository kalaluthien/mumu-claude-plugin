"""What a model's `plan` may change, with the defaults."""
DEFAULTS = {
    "intent": ("", None, "the user's question, in one sentence"),
    "views": ([], "list", "the diagrams a practitioner of this domain expects, each drawn by a level or left out with why"),
    "depth": ("working", ("overview", "working", "detailed"), "overview stops one level below the root; detailed makes every operation one action"),
    "deep": ([], "node ids", "nodes opened even where the depth rules would stop"),
    "shallow": ([], "node ids", "nodes left closed on purpose; the page marks them"),
    "scenarios": ("entry", ("entry", "every"), "entry: a level needs its own Scenario only where something arrives from outside; every: each level does"),
    "prove": ("full", ("full", "rules", "off"), "full: rules, Scenarios and failure paths; rules: only the rules; off: no Alloy"),
    "strict": ([], "check names", "style checks that block instead of warning"),
    "max_nodes": (7, "number", "most nodes on one level"),
    "show": ({"formulas": True, "replay": True, "media": True}, "flags", "what the page shows"),
    "why": ({}, "parameter: sentence", "why each changed default was changed"),
}


def effective(m):
    """The plan in effect: the defaults with the model's overrides."""
    plan = {k: v[0] for k, v in DEFAULTS.items()}
    plan.update(m.get("plan") or {})
    if isinstance(plan["show"], dict):
        plan["show"] = {**DEFAULTS["show"][0], **plan["show"]}
    return plan


def problems(m, opens, check_names):
    """What the schema and the parser cannot say about a plan: every expected view is drawn or explained, deep nodes
    open a level, shallow ones do not, strict names checks, and every changed default says why."""
    out, given = [], m.get("plan") or {}
    if not given.get("views"):
        out.append("plan: list the views a practitioner of this domain expects (views)")
    for v in given.get("views") or []:
        if ("level" in v) == ("why" in v):
            out.append(f'plan: view {v.get("name")} is drawn by a level or left out with why, one of the two')
        elif "level" in v and v["level"] != "root" and v["level"] not in opens:
            out.append(f'plan: view {v.get("name")} names no level {v["level"]}')
    out += [f"plan: deep {n} opens no level" for n in given.get("deep", []) if n not in opens]
    out += [f"plan: {n} is shallow, so it opens no level" for n in given.get("shallow", []) if n in opens]
    out += [f"plan: strict {c} is no check" for c in given.get("strict", []) if c not in check_names]
    changed = [k for k in given if k not in ("intent", "views", "why") and given[k] != DEFAULTS[k][0]]
    out += [f"plan: say why {k} changed (in why)" for k in changed if k not in (given.get("why") or {})]
    return out

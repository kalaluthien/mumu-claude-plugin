"""What a system model's `plan` may change, with the defaults."""
DEFAULTS = {
    "intent": ("", None, "the user's question, in one sentence"),
    "scenarios": ("entry", ("entry", "every"), "entry: a level needs its own Scenario only where something arrives from outside; every: each level does"),
    "prove": ("rules", ("rules", "off"), "rules: --prove asks Alloy whether each dynamic rule holds; off: it asks nothing"),
    "strict": ([], "check names", "style checks that block instead of warning"),
    "why": ({}, "parameter: sentence", "why each changed default was changed"),
    "sources": ([], "paths from root", "the files an analysed system's model rests on; the sources check asks each one cited, and every file they link to or import listed or excluded"),
    "exclude": ({}, "path: reason", "files a listed file links to or imports that the model leaves out, each with a one-line reason"),
    "root": ("", "folder", "where the paths of sources start; empty: the git top-level of the current directory, else the current directory"),
}
LOCAL = ("sources", "exclude", "root")   # facts of one run on one machine: the page never carries them


def effective(m):
    """The plan in effect: the defaults with the model's overrides."""
    plan = {k: v[0] for k, v in DEFAULTS.items()}
    plan.update({k: v for k, v in (m.get("plan") or {}).items() if k in DEFAULTS})   # the drawing's keys are the view's
    return plan


def problems(m, check_names):
    """What the schema and the parser cannot say about a plan: strict names checks, and every changed default says
    why."""
    out, given = [], m.get("plan") or {}
    out += [f"plan: strict {c} is no check" for c in given.get("strict", []) if c not in check_names]
    changed = [k for k in given if k not in ("intent", "why", *LOCAL) and given[k] != DEFAULTS[k][0]]
    out += [f"plan: say why {k} changed (in why)" for k in changed if k not in (given.get("why") or {})]
    return out

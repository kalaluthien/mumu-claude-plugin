"""A verdict file against its grammar ($defs/verdicts in rubric.schema.json) and the spec it grades by."""
from quiz.spec import SCHEMA
from schema.model import shape

VERDICTS = {**SCHEMA["$defs"]["verdicts"], "$defs": SCHEMA["$defs"]}


def criteria(spec):
    return [c for tier in spec["tiers"] for c in tier.get("criteria", [])]


def problems(spec, verdicts, complete=True, groups=False):
    """Each way the file breaks the grammar or the spec, as `where: what`; complete asks a verdict on every criterion
    of every answer, groups asks for groups."""
    if wrong := shape(verdicts, VERDICTS, "verdicts"):
        return [t for _, t in wrong]
    out = []
    known = {c["id"] for c in criteria(spec)}
    pairwise = any(t.get("pairwise") for t in spec["tiers"])
    answers = verdicts["answers"]
    if not answers:
        out.append("verdicts.answers: holds no answer")
    for a, given in answers.items():
        out += [f"verdicts.answers.{a}.{k}: no criterion of the spec" for k in given if k != "beats" and k not in known]
        if complete:
            out += [f"verdicts.answers.{a}: no verdict on {k}" for k in sorted(known - set(given))]
        if "beats" in given and not pairwise:
            out.append(f"verdicts.answers.{a}.beats: the spec has no pairwise tier")
        out += [f"verdicts.answers.{a}.beats: {b} is no answer" for b in given.get("beats", []) if b not in answers]
    seen = set()
    for g, group in enumerate(verdicts.get("groups", [])):
        out += [f"verdicts.groups[{g}]: {a} is no answer" for a in group if a not in answers]
        for a in group:
            if a in seen:
                out.append(f"verdicts.groups[{g}]: {a} is listed twice, in this group or an earlier one")
            seen.add(a)
        if not group:
            out.append(f"verdicts.groups[{g}]: holds no answer")
    if groups and "groups" not in verdicts:
        out.append("verdicts: no groups, which scoring for training needs")
    return out

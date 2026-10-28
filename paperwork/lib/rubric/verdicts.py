"""A verdict file against its grammar ($defs/verdicts in rubric-schema.json) and the spec it grades by."""
from rubric.spec import SCHEMA
from schema.model import shape

VERDICTS = {**SCHEMA["$defs"]["verdicts"], "$defs": SCHEMA["$defs"]}


def criteria(spec):
    return [criterion for tier in spec["tiers"] for criterion in tier.get("criteria", [])]


def problems(spec, verdicts, complete=True, groups=False):
    """Each way the file breaks the grammar or the spec, as `where: what`; complete asks a verdict on every criterion
    of every answer, groups asks for groups."""
    if wrong := shape(verdicts, VERDICTS, "verdicts"):
        return [text for _, text in wrong]
    out = []
    known = {criterion["id"] for criterion in criteria(spec)}
    pairwise = any(tier.get("pairwise") for tier in spec["tiers"])
    answers = verdicts["answers"]
    if not answers:
        out.append("verdicts.answers: holds no answer")
    for answer, given in answers.items():
        out += [f"verdicts.answers.{answer}.{criterion_id}: no criterion of the spec" for criterion_id in given if criterion_id != "beats" and criterion_id not in known]
        if complete:
            out += [f"verdicts.answers.{answer}: no verdict on {criterion_id}" for criterion_id in sorted(known - set(given))]
        if "beats" in given and not pairwise:
            out.append(f"verdicts.answers.{answer}.beats: the spec has no pairwise tier")
        out += [f"verdicts.answers.{answer}.beats: {beaten} is no answer" for beaten in given.get("beats", []) if beaten not in answers]
    seen = set()
    for group_index, group in enumerate(verdicts.get("groups", [])):
        out += [f"verdicts.groups[{group_index}]: {member} is no answer" for member in group if member not in answers]
        for answer in group:
            if answer in seen:
                out.append(f"verdicts.groups[{group_index}]: {answer} is listed twice, in this group or an earlier one")
            seen.add(answer)
        if not group:
            out.append(f"verdicts.groups[{group_index}]: holds no answer")
    if groups and "groups" not in verdicts:
        out.append("verdicts: no groups, which scoring for training needs")
    return out

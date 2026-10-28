"""A grades file against its grammar ($defs/grades in rubric-schema.json) and the spec it grades by."""
import hashlib

from rubric.spec import SCHEMA
from rubric.verdicts import criteria
from schema.model import shape

GRADES = {**SCHEMA["$defs"]["grades"], "$defs": SCHEMA["$defs"]}


def spec_sha(spec_bytes):
    return hashlib.sha256(spec_bytes).hexdigest()[:12]


def judged(grade):
    return grade["met"] is not None


def failing_value(criterion):
    return 0 if criterion["polarity"] == "+" else 1


def failed(criterion, grade):
    """A + criterion not met, or a - criterion whose error is committed; one not judged has not failed."""
    return grade["met"] == failing_value(criterion)


def problems(spec, spec_bytes, grades):
    """Each way the file breaks the grammar or the spec, as `where: what`."""
    if wrong := shape(grades, GRADES, "grades"):
        return [text for _, text in wrong]
    out = []
    if grades["spec_sha"] != spec_sha(spec_bytes):
        out.append(f"grades.spec_sha: {grades['spec_sha']} is not the spec's {spec_sha(spec_bytes)}, "
                   "so the spec changed after grading")
    given, known = grades["grades"], {criterion["id"]: criterion for criterion in criteria(spec)}
    out += [f"grades.grades.{criterion_id}: no criterion of the spec" for criterion_id in given if criterion_id not in known]
    out += [f"grades: no grade for {criterion_id}" for criterion_id in known if criterion_id not in given]
    for criterion_id, grade in given.items():
        if criterion_id not in known:
            continue
        out += [f"grades.grades.{criterion_id}.{field}: empty" for field in ("evidence", "why") if not grade[field].strip()]
        if known[criterion_id]["polarity"] == "+" and grade["met"] == 1 and not grade.get("where", "").strip():
            out.append(f"grades.grades.{criterion_id}: met with no where, so its quote cannot be found; a verdict with no quote is not met")
        if failed(known[criterion_id], grade) and not grade.get("fix", "").strip():
            out.append(f"grades.grades.{criterion_id}: fails, so it needs a fix")
        if "runs" in grade and len(grade["runs"]) != grades["judge"]["runs"]:
            out.append(f"grades.grades.{criterion_id}.runs: {len(grade['runs'])} verdicts, but judge.runs is {grades['judge']['runs']}")
        if grade.get("runs") and len(set(grade["runs"])) > 1 and judged(grade) and not failed(known[criterion_id], grade):
            out.append(f"grades.grades.{criterion_id}.met: the runs split, so it keeps the stricter verdict, a failure")
    return out


def verdicts(spec, grades):
    """The verdict file of the one answer the grades describe, named after the target; a criterion not judged scores as
    failed, since an order must not reward what nobody could check."""
    given = grades["grades"]
    return {"answers": {grades["target"]["name"]: {
        criterion["id"]: given[criterion["id"]]["met"] if judged(given[criterion["id"]]) else failing_value(criterion) for criterion in criteria(spec)}}}

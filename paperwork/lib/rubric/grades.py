"""A grades file against its grammar ($defs/grades in rubric.schema.json) and the spec it grades by."""
import hashlib

from rubric.spec import SCHEMA
from rubric.verdicts import criteria
from schema.model import shape

GRADES = {**SCHEMA["$defs"]["grades"], "$defs": SCHEMA["$defs"]}


def spec_sha(spec_bytes):
    return hashlib.sha256(spec_bytes).hexdigest()[:12]


def failed(criterion, grade):
    """A + criterion not met, or a - criterion whose error is committed."""
    return grade["met"] == (0 if criterion["polarity"] == "+" else 1)


def problems(spec, spec_bytes, grades):
    """Each way the file breaks the grammar or the spec, as `where: what`."""
    if wrong := shape(grades, GRADES, "grades"):
        return [t for _, t in wrong]
    out = []
    if grades["spec_sha"] != spec_sha(spec_bytes):
        out.append(f"grades.spec_sha: {grades['spec_sha']} is not the spec's {spec_sha(spec_bytes)}, "
                   "so the spec changed after grading")
    given, known = grades["grades"], {c["id"]: c for c in criteria(spec)}
    out += [f"grades.grades.{k}: no criterion of the spec" for k in given if k not in known]
    out += [f"grades: no grade for {k}" for k in known if k not in given]
    for k, g in given.items():
        if k not in known:
            continue
        out += [f"grades.grades.{k}.{f}: empty" for f in ("evidence", "why") if not g[f].strip()]
        if failed(known[k], g) and not g.get("fix", "").strip():
            out.append(f"grades.grades.{k}: fails, so it needs a fix")
        if "runs" in g and len(g["runs"]) != grades["judge"]["runs"]:
            out.append(f"grades.grades.{k}.runs: {len(g['runs'])} verdicts, but judge.runs is {grades['judge']['runs']}")
        if g.get("runs") and len(set(g["runs"])) > 1 and not failed(known[k], g):
            out.append(f"grades.grades.{k}.met: the runs split, so it keeps the stricter verdict, a failure")
    return out


def verdicts(spec, grades):
    """The verdict file of the one answer the grades describe, named after the target."""
    return {"answers": {grades["target"]["name"]: {c["id"]: grades["grades"][c["id"]]["met"] for c in criteria(spec)}}}

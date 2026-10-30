"""The one structure check of a rubric, a run file and a grades file; references/grammar.md states their shape."""
import json
import pathlib
import re

from rubric.verdict import majority, rubric_sha

MIN_CRITERIA, MAX_CRITERIA = 7, 20
OVERLAP = 0.6
VAGUE = re.compile(r"\b(appropriate|adequate|proper(ly)?|complete(ly)?|clear(ly)?|good|reasonable|relevant|sufficient)\b"
                   r"|적절|충분|완전한|명확|타당한|잘 ", re.I)
CONJUNCTION = re.compile(r"\band\b|그리고|및|하고 ", re.I)
ABSENCE = re.compile(r"\b(every|all|covers?|lists?|missing)\b|모든|빠짐|누락", re.I)
WORD = re.compile(r"[^\W_]+")

RULES = {
    "form": ("error", "the file fits the grammar's shape"),
    "id-duplicate": ("error", "each criterion id is used once"),
    "check-unknown": ("error", "a criterion's check is judge or program"),
    "critical-missing": ("error", "at least one criterion is critical, since the rating turns on them"),
    "promises-missing": ("error", "the rubric lists the target's promises before its criteria"),
    "flaws-missing": ("error", "the rubric lists the flaw candidates its criteria came from"),
    "command-missing": ("error", "a program check names its command and its fix"),
    "sha-differs": ("error", "the grades name the sha of the rubric they graded by"),
    "grade-missing": ("error", "the grades hold one grade per criterion and no other"),
    "quote-missing": ("error", "a verdict has evidence: a met criterion a quote, a failed one a quote or what was searched"),
    "fix-missing": ("error", "a failed criterion carries a fix"),
    "reason-missing": ("error", "a criterion not judged says why"),
    "items-missing": ("error", "an absence criterion lists its items"),
    "majority-wrong": ("error", "met is the majority of the runs"),
    "criterion-vague": ("warning", "a vague word in a criterion has anchors that say what it means"),
    "criterion-conjunction": ("warning", "a criterion with two or more conjunctions is still one proposition"),
    "criterion-overlap": ("warning", f"two criteria share under {OVERLAP:.0%} of their words, so one flaw is not counted twice"),
    "absence-unmarked": ("warning", "a criterion that asks for every item, or for none missing, is marked absence"),
    "criteria-count": ("warning", f"a rubric holds {MIN_CRITERIA} to {MAX_CRITERIA} criteria"),
}

CRITERION = {"id": str, "text": str, "check": str, "from": str, "critical?": bool, "absence?": bool, "anchors?": str,
             "command?": str, "fix?": str}
PLACE = {"quote": str, "where": str}
ITEM = {"item": str, "found": bool, "quote?": str, "where?": str}
RUBRIC = {
    "target": {"name": str, "where": str, "version": str},
    "subject": {"kind": str, "purpose": str, "reader": str, "frameworks": [str]},
    "promises": [{"text": str, "where": str}],
    "flaws": [str],
    "criteria": [CRITERION],
}
VERDICT = {"met": (int, type(None)), "quote?": str, "where?": str, "searched?": str, "fix?": str, "reason?": str, "items?": [ITEM]}
RUN = {"judge": str, "grades": {"*": VERDICT}, "grader_text": [PLACE]}
GRADE = {**VERDICT, "runs": [(int, type(None))]}
GRADES = {"rubric_sha": str, "judge": {"model": str, "runs": int}, "grades": {"*": GRADE}, "grader_text": [PLACE]}


def shaped(value, form, where):
    """("form", where, what) per break of form: a dict of key (`?` optional, `*` any) to form, a one-item list, or a type."""
    if isinstance(form, list):
        if not isinstance(value, list):
            return [("form", where, "is not a list")]
        return [row for i, item in enumerate(value) for row in shaped(item, form[0], f"{where}[{i}]")]
    if not isinstance(form, dict):
        return [] if isinstance(value, form) and not isinstance(value, bool) or form is bool and isinstance(value, bool) \
            else [("form", where, f"is not {form}")]
    if not isinstance(value, dict):
        return [("form", where, "is not an object")]
    if "*" in form:
        return [row for key, item in value.items() for row in shaped(item, form["*"], f"{where}.{key}")]
    keys = {key.rstrip("?"): (key, field) for key, field in form.items()}
    out = [("form", f"{where}.{key}", "is not in the grammar") for key in value if key not in keys]
    out += [("form", f"{where}.{name}", "is missing") for name, (key, _) in keys.items() if name not in value and not key.endswith("?")]
    return out + [row for name, (_, field) in keys.items() if name in value for row in shaped(value[name], field, f"{where}.{name}")]


def overlaps(criteria):
    out = []
    for i, first in enumerate(criteria):
        for second in criteria[i + 1:]:
            one, other = set(WORD.findall(first["text"].lower())), set(WORD.findall(second["text"].lower()))
            common, either = one & other, one | other
            if either and len(common) / len(either) >= OVERLAP:
                out.append(("criterion-overlap", f"rubric.criteria.{second['id']}", f"shares {len(common) / len(either):.0%} of its words with {first['id']}"))
    return out


def rubric_problems(rubric):
    if wrong := shaped(rubric, RUBRIC, "rubric"):
        return wrong
    criteria, out = rubric["criteria"], []
    ids = [criterion["id"] for criterion in criteria]
    out += [("id-duplicate", "rubric.criteria", f"{name} is used {ids.count(name)} times") for name in sorted(set(ids)) if ids.count(name) > 1]
    if not any(criterion.get("critical") for criterion in criteria):
        out.append(("critical-missing", "rubric.criteria", "no criterion is critical"))
    if not rubric["promises"]:
        out.append(("promises-missing", "rubric.promises", "lists no promise"))
    if not rubric["flaws"]:
        out.append(("flaws-missing", "rubric.flaws", "lists no flaw candidate"))
    if not MIN_CRITERIA <= len(criteria) <= MAX_CRITERIA:
        out.append(("criteria-count", "rubric.criteria", f"holds {len(criteria)}"))
    for criterion in criteria:
        at, text = f"rubric.criteria.{criterion['id']}", criterion["text"]
        if criterion["check"] not in ("judge", "program"):
            out.append(("check-unknown", at, f"{criterion['check']!r} is neither judge nor program"))
        if criterion["check"] == "program" and not (criterion.get("command") and criterion.get("fix")):
            out.append(("command-missing", at, "a program check needs a command and a fix"))
        if (match := VAGUE.search(text)) and not criterion.get("anchors"):
            out.append(("criterion-vague", at, f"{match.group(0).strip()!r} has no anchors"))
        if (n := len(CONJUNCTION.findall(text))) >= 2:
            out.append(("criterion-conjunction", at, f"{n} conjunctions; split it unless they are one condition"))
        if ABSENCE.search(text) and not criterion.get("absence") and criterion["check"] == "judge":
            out.append(("absence-unmarked", at, "reads as an absence criterion"))
    return out + overlaps(criteria)


def verdict_problems(criterion, verdict, at):
    met, out = verdict["met"], []
    if met not in (0, 1, None):
        return [("form", f"{at}.met", f"{met} is not 0, 1 or null")]
    if met is None:
        return [("reason-missing", at, "not judged, with no reason")] if not verdict.get("reason", "").strip() else []
    if criterion.get("absence"):
        if not verdict.get("items"):
            out.append(("items-missing", at, "an absence criterion lists its items"))
    elif not verdict.get("quote", "").strip() and (met or not verdict.get("searched", "").strip()):
        out.append(("quote-missing", at, "a verdict with no evidence"))
    if not met and not verdict.get("fix", "").strip():
        out.append(("fix-missing", at, "fails, so it needs a fix"))
    return out


def run_problems(rubric, run):
    """Every problem of one run file, whose criteria are those of its calls, so it may hold only some."""
    if wrong := shaped(run, RUN, "run"):
        return wrong
    known, out = {criterion["id"]: criterion for criterion in rubric["criteria"]}, []
    for name, verdict in run["grades"].items():
        if name not in known:
            out.append(("grade-missing", f"run.grades.{name}", "no criterion of the rubric"))
        else:
            out += verdict_problems(known[name], verdict, f"run.grades.{name}")
    return out


def grades_problems(rubric, rubric_bytes, grades):
    if wrong := shaped(grades, GRADES, "grades"):
        return wrong
    known, given = {criterion["id"]: criterion for criterion in rubric["criteria"]}, grades["grades"]
    out = []
    if grades["rubric_sha"] != rubric_sha(rubric_bytes):
        out.append(("sha-differs", "grades.rubric_sha", f"{grades['rubric_sha']} is not the rubric's {rubric_sha(rubric_bytes)}, so it changed after grading"))
    out += [("grade-missing", f"grades.grades.{name}", "no criterion of the rubric") for name in given if name not in known]
    out += [("grade-missing", "grades.grades", f"no grade for {name}") for name in known if name not in given]
    for name, grade in given.items():
        if name in known:
            out += verdict_problems(known[name], grade, f"grades.grades.{name}")
            if grade["met"] != majority(grade["runs"]):
                out.append(("majority-wrong", f"grades.grades.{name}", f"met is {grade['met']}, the majority of {grade['runs']} is {majority(grade['runs'])}"))
    return out


class Refused(Exception):
    pass


def errors(rows):
    return [row for row in rows if RULES[row[0]][0] == "error"]


def line(row):
    rule, where, message = row
    return f"{'warning ' if RULES[rule][0] == 'warning' else ''}{where}: {rule}: {message}"


def read_rubric(path):
    rubric_bytes = pathlib.Path(path).read_bytes()
    rubric = json.loads(rubric_bytes)
    if wrong := errors(rubric_problems(rubric)):
        raise Refused(f"{path}: {line(wrong[0])}")
    return rubric, rubric_bytes

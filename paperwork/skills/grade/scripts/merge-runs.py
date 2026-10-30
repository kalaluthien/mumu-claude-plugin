#!/usr/bin/env python3
"""Merge the judges' run files into one grades file: check each quote, run each program check, take the majority.

usage: merge-runs.py RUBRIC.json SOURCE_DIR RUNS_DIR OUT.json   RUNS_DIR holds run-<r>-call-<c>.json
"""
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))

from rubric.check import Refused, errors, grades_problems, line, read_rubric, run_problems  # noqa: E402
from rubric.verdict import RUNS, gaps, majority, rating, rubric_sha, status  # noqa: E402

PLACE = re.compile(r"^(.+?)(?::(\d+)(?:-(\d+))?)?$")
RUN_FILE = re.compile(r"^run-(\d+)-call-\d+\.json$")
GRADER_TEXT = re.compile(r"\b(note|dear|attention|message|hello|hi)\b.{0,12}\b(grader|judge|evaluator|reviewer|model|LLM|AI)s?\b"
                         r"|\b(ignore|disregard)\b.{0,30}\b(instructions|rubric|criteria)\b"
                         r"|\b(give|award|rate)\b.{0,30}\b(full|top|highest|perfect)\s+(marks?|scores?|grades?|ratings?)\b|채점자|평가자", re.I)
QUOTE_LIMIT = 300
COMMAND_SECONDS = 120


def flat(text):
    return " ".join(text.split())


def quote_found(source, quote, where):
    match = PLACE.match(where or "")
    path = pathlib.Path(source) / match.group(1) if match else None
    if path is None or not path.is_file() or not quote.strip() or len(quote) > QUOTE_LIMIT:
        return False
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    first = int(match.group(2) or 1)
    last = int(match.group(3) or match.group(2) or len(lines))
    return flat(quote) in flat(" ".join(lines[first - 1:last]))


def not_judged(reason, verdict):
    return {"met": None, "reason": reason, "where": verdict.get("where", "")}


def checked(source, criterion, verdict):
    """The verdict, or not judged when its evidence does not hold, since a bad quote says nothing about the target."""
    if verdict["met"] is None:
        return verdict
    if criterion.get("absence"):
        items = verdict["items"]
        if any(item["found"] and not quote_found(source, item.get("quote", ""), item.get("where", "")) for item in items):
            return not_judged("an item's quote was not found at its place", verdict)
        if bool(verdict["met"]) != all(item["found"] for item in items):
            return not_judged("the verdict does not follow from its items", verdict)
        return verdict
    if verdict.get("quote") and not quote_found(source, verdict["quote"], verdict.get("where", "")):
        return not_judged("the quote was not found at its place", verdict)
    return verdict


def read_runs(rubric, folder):
    runs, judges, grader_text = {}, set(), []
    for path in sorted(pathlib.Path(folder).iterdir()):
        if not (name := RUN_FILE.match(path.name)):
            continue
        run = json.loads(path.read_text(encoding="utf-8"))
        if wrong := errors(run_problems(rubric, run)):
            raise Refused(f"{path.name}: {line(wrong[0])}")
        runs.setdefault(int(name.group(1)), {}).update(run["grades"])
        judges.add(run["judge"])
        grader_text += run["grader_text"]
    return runs, sorted(judges), grader_text


def scanned_text(source):
    """Passages that address a grader, found without a judge, since a judge the passage fooled would not report it."""
    root = pathlib.Path(source)
    for path in sorted(path for path in root.rglob("*") if path.is_file() and ".git" not in path.parts):
        for i, text in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if GRADER_TEXT.search(text):
                yield {"quote": text.strip()[:QUOTE_LIMIT], "where": f"{path.relative_to(root)}:{i}"}


def program_grade(source, criterion):
    done = subprocess.run(criterion["command"], shell=True, cwd=source, capture_output=True, text=True, timeout=COMMAND_SECONDS)
    met = int(done.returncode == 0)
    grade = {"met": met, "runs": [met], "quote": flat(done.stdout + done.stderr)[-200:] or f"exit {done.returncode}", "where": criterion["command"]}
    return grade if met else {**grade, "fix": criterion["fix"]}


def judged_grade(source, criterion, runs):
    verdicts = [checked(source, criterion, run[criterion["id"]]) for run in runs.values() if criterion["id"] in run]
    # A lost call file must not let fewer judges decide, so the count is the briefs' own, never the files found.
    if len(verdicts) < RUNS:
        raise Refused(f"{criterion['id']} has {len(verdicts)} of {RUNS} runs")
    votes = [verdict["met"] for verdict in verdicts]
    met = majority(votes)
    kept = next((verdict for verdict in verdicts if verdict["met"] == met), None) or not_judged("the runs reach no majority", verdicts[0])
    # A dissenting run's fix and place stay, since a person settling the split needs them.
    dissent = {key: verdict[key] for verdict in reversed(verdicts) for key in ("fix", "where") if verdict.get(key)}
    grade = {**dissent, **{key: value for key, value in kept.items() if value}, "met": kept["met"], "runs": votes}
    return {key: value for key, value in grade.items() if key != "fix"} if set(votes) == {1} else grade


def merge(rubric_path, source, folder):
    rubric, rubric_bytes = read_rubric(rubric_path)
    runs, judges, grader_text = read_runs(rubric, folder)
    grades = {criterion["id"]: program_grade(source, criterion) if criterion["check"] == "program" else judged_grade(source, criterion, runs)
              for criterion in rubric["criteria"]}
    reported = [passage for passage in grader_text if quote_found(source, passage["quote"], passage["where"])]
    found = list({passage["where"]: passage for passage in [*reported, *scanned_text(source)]}.values())
    merged = {"rubric_sha": rubric_sha(rubric_bytes), "judge": {"model": ", ".join(judges) or "no judge", "runs": len(runs)}, "grades": grades, "grader_text": found}
    if wrong := errors(grades_problems(rubric, rubric_bytes, merged)):
        raise Refused(line(wrong[0]))
    return rubric, merged


def main(args):
    if len(args) != 4 or any(argument.startswith("-") for argument in args):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        rubric, merged = merge(*args[:3])
        pathlib.Path(args[3]).write_text(json.dumps(merged, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    except (Refused, OSError, ValueError, subprocess.TimeoutExpired) as e:
        print(f"refused: {e}")
        return 1
    for criterion in rubric["criteria"]:
        grade = merged["grades"][criterion["id"]]
        print(f"{criterion['id']}: {status(criterion, grade)}, {grade['runs'].count(1)} of {len(grade['runs'])} runs")
    for passage in merged["grader_text"]:
        print(f"grader text: {passage['where']}: {passage['quote']}")
    critical, other = gaps(rubric, merged)
    print(f"Rating {rating(critical, other)}: {critical} critical gaps and {other} other gaps. A run count shows how far the "
          f"runs agree, not how often they are right.")
    if merged["judge"]["runs"] and "," not in merged["judge"]["model"]:
        print("One model ran every call, so its blind spots are shared; use another model family when the session has one.")
    print(f"wrote {args[3]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

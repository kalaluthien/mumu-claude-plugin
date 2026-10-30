#!/usr/bin/env python3
"""Check a rubric, and the grades made by it, against the grammar and the rules it cannot state.

usage: check-rubric.py check RUBRIC.json [GRADES.json]   print each problem as `where: rule: message`, then `ok`
       check-rubric.py fixtures                          check every file in fixtures/: X.rubric.json must be rejected, or
                                                           warned on, by rule X alone and X.grades.json likewise, against
                                                           ok.rubric.json; ok.rubric.json must draw nothing
       check-rubric.py rules                             list each rule, error or warning, and what it asks
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))

from rubric.check import RULES, errors, grades_problems, line, rubric_problems  # noqa: E402

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures"


def check(rubric_path, grades_path=None):
    try:
        rubric_bytes = pathlib.Path(rubric_path).read_bytes()
        rubric = json.loads(rubric_bytes)
        rows = rubric_problems(rubric)
        if grades_path and not errors(rows):
            rows += grades_problems(rubric, rubric_bytes, json.loads(pathlib.Path(grades_path).read_text(encoding="utf-8")))
    except (OSError, ValueError) as e:
        print(f"not read: {e}")
        return 1
    for row in rows:
        print(line(row))
    if errors(rows):
        print(f"{len(errors(rows))} error(s)")
        return 1
    print("ok")
    return 0


def fixture_rows(fixture):
    good_bytes = (FIXTURES / "ok.rubric.json").read_bytes()
    good = json.loads(good_bytes)
    document = json.loads(fixture.read_text(encoding="utf-8"))
    return grades_problems(good, good_bytes, document) if fixture.name.endswith(".grades.json") else rubric_problems(document)


def fixtures():
    files, failed = sorted(FIXTURES.glob("*.json")), 0
    for fixture in files:
        name, rows = fixture.name.split(".")[0], fixture_rows(fixture)
        rules = {row[0] for row in rows}
        good = rules == (set() if name == "ok" else {name})
        failed += not good
        print(f"{'ok  ' if good else 'FAIL'}  {fixture.name}: {', '.join(sorted(rules)) or 'nothing'}")
    unnamed = sorted(set(RULES) - {fixture.name.split(".")[0] for fixture in files})
    for rule in unnamed:
        print(f"FAIL  no fixture names rule {rule}")
    print("Each fixture draws only the rule it is named after, so each rule is shown to fire alone.")
    print(f"fixtures {failed + len(unnamed)} failed" if failed or unnamed else "fixtures ok")
    return 1 if failed or unnamed else 0


def main(args):
    if len(args) in (2, 3) and args[0] == "check":
        return check(*args[1:])
    if args == ["fixtures"]:
        return fixtures()
    if args == ["rules"]:
        for rule, (severity, asks) in RULES.items():
            print(f"{rule} {severity} {asks}")
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

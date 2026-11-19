#!/usr/bin/env python3
"""Grade how a manager session routes each owner request by the manager playbook, from the answer a `claude -p` run of
`owner-routes/prompt.md` printed, and print `PASS` or `FAIL` with one line per gap.

usage: replay-owner-routes.py
usage: replay-owner-routes.py one-table|fold-cases|same-actions|report-form [<manager-file>]

With no argument it grades the saved answers in `owner-routes/`: `answer-head.txt` must pass every mode against the
playbook, and `answer-base.txt`, an answer to the playbook before one table routed every request, must fail
`one-table`, `fold-cases` and `report-form` against `owner-routes/manager-base.txt`; it prints `PASS` when both hold.
A mode reads the answer on stdin and the playbook at `teamwork/skills/kick-off/references/manager.md`, or the file given:

- `one-table`: every case is routed by a row of the one table under `## Steps`, that row named exactly.
- `fold-cases`: the Triage step's opening line, its table and its report form hold fewer words than `BASE_WORDS`, the
  old triage step and the five rules that routed owner requests, counting any of those rules still present; some row routes two cases or more; and
  every row routes a case.
- `same-actions`: every case is routed by that table to the operations it had before, as `owner-routes/expected.json` lists.
- `report-form`: the status check and the progress report each have a row of their own, the playbook sets a
  `**Report form**` of three columns or more, and both replies open their table with one same header of that many columns."""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "owner-routes"
MANAGER = HERE.parent / "references" / "manager.md"
BASE_WORDS = 655
OLD_RULES = ("Tool prompt", "Work style", "Follow-up", "Usage limit", "Next step")
MODES = ("one-table", "fold-cases", "same-actions", "report-form")


def usage():
    print(__doc__, file=sys.stderr)
    return 2


def read_answer(text):
    blocks = re.findall(r"```json\s*\n(.*?)\n```", text, re.S)
    if not blocks:
        return None
    try:
        answer = json.loads(blocks[-1])
    except json.JSONDecodeError:
        return None
    return answer if isinstance(answer, dict) and isinstance(answer.get("cases"), dict) else None


def cells(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def route_table(lines):
    """The first table under `## Steps`: its row lines, header and separator dropped."""
    section = None
    rows = []
    for line in lines:
        if line.startswith("## "):
            if rows:
                break
            section = line[3:].strip()
            continue
        if section != "Steps":
            continue
        if line.strip().startswith("|"):
            rows.append(line)
        elif rows:
            break
    return rows[2:], rows


def report_columns(lines):
    for line in lines:
        if line.strip().startswith("**Report form**"):
            return re.findall(r"`([^`]+)`", line.split("**Report form**", 1)[1].split(";")[0]), line
    return [], ""


def reply_header(reply):
    for line in reply.splitlines():
        if line.strip().startswith("|"):
            return [cell.casefold() for cell in cells(line)]
    return []


def grade(mode, answer, manager):
    lines = manager.read_text().splitlines()
    rows, table_lines = route_table(lines)
    firsts = [cells(row)[0] for row in rows]
    expected = json.loads((DATA / "expected.json").read_text())
    if answer is None:
        return ["answer holds no json block with `cases`"]
    cases = answer["cases"]
    gaps = []
    routed = {}
    for name in expected:
        case = cases.get(name) or {}
        if case.get("section") == "Steps" and case.get("locator") in firsts:
            routed[name] = case["locator"]
    if mode == "one-table":
        gaps += [f"{name}: routed by {cases.get(name, {}).get('section')} {cases.get(name, {}).get('locator')!r}"
                 for name in expected if name not in routed]
    elif mode == "fold-cases":
        columns, form_line = report_columns(lines)
        rules = [line for line in lines if re.match(r"- \*\*(%s)\*\*" % "|".join(map(re.escape, OLD_RULES)), line)]
        step = [line for line in lines if line.startswith("2. **Triage**")]
        words = sum(len(line.split()) for line in step + table_lines + [form_line] + rules)
        if words >= BASE_WORDS:
            gaps.append(f"triage step, report form and old rules hold {words} words, not fewer than {BASE_WORDS}")
        counts = {first: list(routed.values()).count(first) for first in firsts}
        if not any(n >= 2 for n in counts.values()):
            gaps.append("no row routes two cases")
        gaps += [f"row routes no case: {first}" for first, n in counts.items() if n == 0]
        gaps += [f"{name}: not routed by the table" for name in expected if name not in routed]
    elif mode == "same-actions":
        for name, rule in expected.items():
            operations = [str(op).strip("`") for op in (cases.get(name) or {}).get("operations", [])]
            if name not in routed:
                gaps.append(f"{name}: not routed by the table")
            missing = [op for op in rule["needs"] if op not in operations]
            extra = [op for op in rule["never"] if op in operations]
            if missing or extra:
                gaps.append(f"{name}: operations {operations}, lacking {missing}, with {extra}")
    else:
        status, progress = routed.get("status-check"), routed.get("progress-report")
        if not status or not progress or status == progress:
            gaps.append(f"status check and progress report need a row each, got {status!r} and {progress!r}")
        columns, _ = report_columns(lines)
        if len(columns) < 3:
            gaps.append(f"playbook sets no **Report form** of three columns or more: {columns}")
        headers = [reply_header(str(answer.get(key, ""))) for key in ("status-reply", "progress-reply")]
        if not headers[0] or headers[0] != headers[1]:
            gaps.append(f"replies open with different table headers: {headers}")
        elif columns and len(headers[0]) != len(columns):
            gaps.append(f"reply header has {len(headers[0])} columns, the form {len(columns)}")
    return gaps


def replay():
    failures = []
    head = read_answer((DATA / "answer-head.txt").read_text())
    for mode in MODES:
        gaps = grade(mode, head, MANAGER)
        if gaps:
            failures.append(f"answer-head {mode}: {gaps[0]}")
    base = read_answer((DATA / "answer-base.txt").read_text())
    for mode in ("one-table", "fold-cases", "report-form"):
        if not grade(mode, base, DATA / "manager-base.txt"):
            failures.append(f"answer-base {mode}: passed")
    for line in failures:
        print(line)
    print("FAIL" if failures else "PASS")
    return 1 if failures else 0


def main(args):
    if not args:
        return replay()
    if args[0] not in MODES or len(args) > 2 or any(arg.startswith("-") for arg in args):
        return usage()
    manager = pathlib.Path(args[1]) if len(args) == 2 else pathlib.Path("teamwork/skills/kick-off/references/manager.md")
    if not manager.is_file():
        return usage()
    gaps = grade(args[0], read_answer(sys.stdin.read()), manager)
    for gap in gaps:
        print(gap)
    print("FAIL" if gaps else "PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Print each criterion of a task body's Definition of done whose form a judge would send back, or run-criteria.py cannot read, one line per criterion,
`<position>: <defects>`, and exit 1; a body with none prints nothing and exits 0.

usage: check-criteria.py <task> [--repository <folder>]
usage: check-criteria.py [--task <task>] <body-file | -> [--repository <folder>]
usage: check-criteria.py --title <title>
usage: check-criteria.py --reason <what changed>
usage: check-criteria.py --cut-off

`--repository` names the checkout, main or worktree, whose board a task is read from, with no `cd`; a body-file path is read from that folder. A task is its number, `#n` or url; given alone it is read from the board, body and number. A word that names no file and no task
on the board prints one line saying which, exit 1.

It reads the form only, never running a command, since whether a check passes on the base stays the judge's to find.
After the lines it prints, once per defect named, what the defect means and how to fix it.

A task numbered at or above `CUT_OFF`, or one given with no `--task`, must also hold at most 5 criteria, `[task]` parts
not counted, each `[check]` a scenario that prints `PASS`, on base `FAIL`, none running `check-repository.py`, and none only a text scan, such as a grep, an
`awk` or inline code that reads a file and runs nothing, and a check that starts a live session (`claude -p`) must run it as its
first pipe stage and say `watches: <path>...`, so run-criteria.py can replay its transcript. A task below it keeps the rules it was filed under.
`--cut-off` prints `CUT_OFF`.

`--title` and `--reason` print a `write: <defect>` line for each defect `use-board.py file` or `title` would refuse in the title, or `edit` in its `--reason`
line, and exit 1; a text they accept prints nothing and exits 0.

Under the same rule it prints a `write: <defect>` line for each defect `use-board.py file` would refuse in the body, its summary line, headings and criterion names
included, and exits 1; `edit` refuses only the defects the stored body did not already hold, so a `write:` line it keeps is no refusal of an edit.
`file` and `edit` also refuse each line this lint prints on the new body, by the same `criteria_check.body_refusals`.

A task numbered at or above `criteria_check.GOAL_CUT_OFF`, or one given with no `--task`, whose body holds a `## Goal` must also have in it a `Path:` line
naming the flow of the changed part, as protocol.md's **Scope the path** defines it; the lint prints it as `goal: <defects>`. A body with no Goal, such as a root, is not checked."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board  # noqa: E402
import board_refs  # noqa: E402
import criteria_check  # noqa: E402
import data_folder  # noqa: E402
import task_state  # noqa: E402

def main(args):
    args = data_folder.enter(args, __doc__)
    if args == ["--cut-off"]:
        print(criteria_check.CUT_OFF)
        return 0
    if len(args) == 2 and args[0] in ("--title", "--reason"):
        written = task_state.defects("title" if args[0] == "--title" else "reason", args[1])
        for found in written:
            print(f"write: {found}")
        return 1 if written else 0
    task = None
    if len(args) == 3 and args[0] == "--task" and not args[1].startswith("-"):
        try:
            task, args = board_refs.TaskRef.parse(args[1]).number, args[2:]
        except board_refs.Refused as e:
            sys.exit(f"check-criteria: --task wants a task's number or url, and {args[1]} {e}")
    if len(args) != 1 or args[0].startswith("-") and args[0] != "-":
        print(__doc__, file=sys.stderr)
        return 2
    source = args[0]
    if source == "-":
        body = sys.stdin.read()
    elif len(source) < 1024 and "\n" not in source and pathlib.Path(source).is_file():
        try:
            body = pathlib.Path(source).read_text()
        except (OSError, UnicodeDecodeError) as e:
            sys.exit(f"check-criteria: could not read {source}: {e}")
    elif task is None:
        try:
            task = board_refs.TaskRef.parse(source).number
        except board_refs.Refused as e:
            sys.exit(f"check-criteria: {source} is no file here, and {e}")
        try:
            found = board.fresh(task, comments=False)
        except LookupError as e:
            sys.exit(f"check-criteria: {e}")
        body = found["body"] if found else sys.exit(f"check-criteria: the board holds no task #{task}")
    else:
        sys.exit(f"check-criteria: {source} is no file here")
    new_rules = task is None or task >= criteria_check.CUT_OFF
    flagged = [(position, found) for position, _, found in criteria_check.lint(body, task)]
    # `file` and `edit` refuse a body that breaks the Plain words caps, so a lint that passes it would only move the refusal to the write
    written = task_state.defects("file", body) if new_rules else []
    for position, found in flagged:
        print(f"{position}: {', '.join(found)}")
    for name in dict.fromkeys(defect for _, found in flagged for defect in found):
        print(f"- {name}: {criteria_check.FIX[name.split(' by ')[0]]}")
    for found in written:
        print(f"write: {found}")
    if written:
        print("- write: `use-board.py file` would refuse this body, and `edit` would refuse each defect the stored body does not already hold; fix the line it names")
    return 1 if flagged or written else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

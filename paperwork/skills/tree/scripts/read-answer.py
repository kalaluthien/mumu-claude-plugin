#!/usr/bin/env python3
"""Apply an owner's Answer to a plan and print the next plan.

usage: read-answer.py PLAN.json ANSWER.md        next plan JSON on stdout, "not answered: <id> <text>" on stderr per Decision left open; "refused: line N: ..." and exit 1 when the Answer does not apply
"""
import json
import pathlib
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import tree_plan  # noqa: E402


def next_plan(plan_path, answer_path):
    plan = tree_plan.load_file(plan_path)
    answer_text = pathlib.Path(answer_path).read_text(encoding="utf-8")
    tree_plan.check_head(plan, answer_text)
    entries = tree_plan.parse_answer(answer_text)
    new = tree_plan.apply_answer(plan, entries)
    left = tree_plan.unanswered(plan, entries)
    errors = tree_plan.check(new)
    if errors:
        raise tree_plan.AnswerError(0, f"the next plan fails the checker: {errors[0][0]}: {errors[0][1]}")
    return new, left


def main(args):
    if len(args) != 2 or any(argument.startswith("--") for argument in args):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        new, left = next_plan(*args)
    except tree_plan.AnswerError as e:
        print(f"refused: {e}")
        return 1
    except (tree_plan.PlanError, OSError) as e:
        print(f"refused: {e}")
        return 1
    for part_id, text in left:
        print(f"not answered: {part_id} {text}", file=sys.stderr)
    print(json.dumps(new, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

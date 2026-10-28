#!/usr/bin/env python3
"""Apply an owner's Answer to a plan and print the next plan.

usage: read-answer.py PLAN.json ANSWER.md        next plan JSON on stdout; "refused: line N: ..." and exit 1 when the Answer does not apply
       read-answer.py --expect-refused PLAN ANSWER...   "refused K of N": each Answer must be refused against PLAN
       read-answer.py --check DIR                "ok N": each X.json with an X.answer.md applies and the result passes the checker
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
    errors = tree_plan.check(new)
    if errors:
        raise tree_plan.AnswerError(0, f"the next plan fails the checker: {errors[0][0]}: {errors[0][1]}")
    return new


def main(args):
    if len(args) == 2 and args[0] == "--check":
        n = 0
        for answer in sorted(pathlib.Path(args[1]).glob("*.answer.md")):
            plan = answer.with_name(answer.name[: -len(".answer.md")] + ".json")
            try:
                next_plan(plan, answer)
            except (tree_plan.AnswerError, tree_plan.PlanError, OSError) as e:
                print(f"refused: {answer.name}: {e}")
                return 1
            n += 1
        if n == 0:
            print("refused: no X.answer.md file found")
            return 1
        print(f"ok {n}")
        return 0
    if len(args) >= 3 and args[0] == "--expect-refused":
        plan, answers = args[1], args[2:]
        refused = []
        for answer in answers:
            try:
                next_plan(plan, answer)
            except (tree_plan.AnswerError, tree_plan.PlanError) as e:
                refused.append(f"{pathlib.Path(answer).name}: {e}")
        for line in refused:
            print(line)
        print(f"refused {len(refused)} of {len(answers)}")
        return 0 if len(refused) == len(answers) else 1
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        new = next_plan(*args)
    except tree_plan.AnswerError as e:
        print(f"refused: {e}")
        return 1
    except (tree_plan.PlanError, OSError) as e:
        print(f"refused: {e}")
        return 1
    print(json.dumps(new, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

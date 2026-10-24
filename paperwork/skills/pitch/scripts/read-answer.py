#!/usr/bin/env python3
"""Apply an owner's Answer to a plan and print the next plan.

  read-answer.py PLAN.json ANSWER.md   next plan JSON on stdout; "refused: line N: ..." and exit 1 when the Answer does not apply
  read-answer.py --check DIR           "ok N": each X.json with an X.answer.md applies and the result passes the checker
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
import pitch_plan  # noqa: E402


def next_plan(plan_path, answer_path):
    plan = pitch_plan.load_file(plan_path)
    md = Path(answer_path).read_text(encoding="utf-8")
    pitch_plan.check_head(plan, md)
    entries = pitch_plan.parse_answer(md)
    new = pitch_plan.apply_answer(plan, entries)
    errs = pitch_plan.check(new)
    if errs:
        raise pitch_plan.AnswerError(0, f"the next plan fails the checker: {errs[0][0]}: {errs[0][1]}")
    return new


def main(argv):
    if len(argv) == 2 and argv[0] == "--check":
        n = 0
        for answer in sorted(Path(argv[1]).glob("*.answer.md")):
            plan = answer.with_name(answer.name[: -len(".answer.md")] + ".json")
            try:
                next_plan(plan, answer)
            except (pitch_plan.AnswerError, pitch_plan.PlanError, OSError) as e:
                print(f"refused: {answer.name}: {e}")
                return 1
            n += 1
        if n == 0:
            print("refused: no X.answer.md file found")
            return 1
        print(f"ok {n}")
        return 0
    if len(argv) != 2:
        print("usage: read-answer.py PLAN.json ANSWER.md | read-answer.py --check DIR")
        return 2
    try:
        new = next_plan(*argv)
    except pitch_plan.AnswerError as e:
        print(f"refused: {e}")
        return 1
    except (pitch_plan.PlanError, OSError) as e:
        print(f"refused: {e}")
        return 1
    print(json.dumps(new, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

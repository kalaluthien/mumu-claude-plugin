#!/usr/bin/env python3
"""Check tree plan files against the grammar.

usage: check-plan.py FILE...                   prints "ok N", or one error per line and exits 1
       check-plan.py --expect-refused FILE...  prints "<file>: <rule>" per refused file, then "refused K of N"
"""
import os
import pathlib
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import tree_plan  # noqa: E402


def errors_of(path):
    try:
        return tree_plan.check(tree_plan.load_file(path))
    except tree_plan.PlanError as e:
        return [(e.path, e.rule, e.detail)]
    except OSError as e:
        return [("$", "unreadable", str(e))]


def main(args):
    expect = "--expect-refused" in args
    files = [argument for argument in args if argument != "--expect-refused"]
    if not files or any(argument.startswith("--") for argument in files):
        print(__doc__, file=sys.stderr)
        return 2
    if not expect:
        bad = 0
        for file in files:
            for path, rule, detail in errors_of(file):
                bad += 1
                print(f"{file}: {path}: {rule}: {detail}")
        if bad:
            print(f"refused: {bad} error(s) above; fix them and run again")
            return 1
        print(f"ok {len(files)}")
        return 0
    refused = total = 0
    for file in sorted(files, key=os.path.basename):
        name = os.path.basename(file)
        errors = errors_of(file)
        # A *-plan.json is the valid plan an answer fixture is applied to, so it is
        # checked to be accepted and is not counted as a refused fixture.
        if name.endswith("-plan.json"):
            if errors:
                print(f"{name}: expected to be accepted but was refused: {errors[0][1]}")
                return 1
            continue
        total += 1
        if errors:
            refused += 1
            print(f"{name}: {errors[0][1]}")
        else:
            print(f"{name}: accepted, but a refused fixture must be refused")
    print(f"refused {refused} of {total}")
    return 0 if refused == total else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

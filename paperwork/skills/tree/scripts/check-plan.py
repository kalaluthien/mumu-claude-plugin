#!/usr/bin/env python3
"""Check tree plan files against the grammar.

usage: check-plan.py FILE...   prints "ok N", or one error per line and exits 1
"""
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
    if not args or any(argument.startswith("--") for argument in args):
        print(__doc__, file=sys.stderr)
        return 2
    bad = 0
    for file in args:
        for path, rule, detail in errors_of(file):
            bad += 1
            print(f"{file}: {path}: {rule}: {detail}")
    if bad:
        print(f"refused: {bad} error(s) above; fix them and run again")
        return 1
    print(f"ok {len(args)}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

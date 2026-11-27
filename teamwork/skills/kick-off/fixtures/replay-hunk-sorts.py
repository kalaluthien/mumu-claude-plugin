#!/usr/bin/env python3
"""Run run-criteria.py `--hunks` on a temporary git repository whose change adds a script that prints its arguments sorted and counts them
sorted by length. Print `ok <case>` or `fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `order-kills`: under a check that needs the printed order, the sort of the printed names, made `list(names)`, is killed, while the sort
  of the counted names, whose order nothing reads, is named a surviving mutant that becomes `list(set(names))`, exit 1;
- `order-ignored`: under a check that reads only the count, both sorts are named surviving mutants, exit 1.

usage: replay-hunk-sorts.py"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
BODY = "## Definition of done\n\n1. [check] **The tool prints its names**: `python3 tool.py b a b | {filter}` prints `{text}`; on base nothing.\n"
TOOL = '''import sys

names = sys.argv[1:]
print(" ".join(sorted(names)))
print(len(sorted(set(names), key=len)))
'''
PRINTED = "tool.py:4: surviving mutant: no criterion fails when the sort `sorted(names)` becomes `list(names)`, so make a criterion fail on it or drop it"
COUNTED = "tool.py:5: surviving mutant: no criterion fails when the sort `sorted(set(names), key=len)` becomes `list(set(names))`, so make a criterion fail on it or drop it"


def sweep(box, filter, text):
    """(exit code, the lines naming a surviving sort, all it printed) of a `--hunks` sweep whose check pipes the tool through FILTER."""
    done = box.python(SCRIPT, "--hunks", "--ref", "main", replay_probe.write_text(box.work, "body.md", BODY.format(filter=filter, text=text)), timeout=300)
    out = done.stdout + done.stderr
    return done.returncode, {line for line in out.splitlines() if "the sort `" in line}, out


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("hunk-sorts-") as work:
        box = replay_probe.Sandbox(work)
        box.git("checkout", "-qb", "change")
        (box.repository / "tool.py").write_text(TOOL)
        box.git("add", "-A")
        box.git("commit", "-qm", "change")
        code, sorts, out = sweep(box, "paste -sd, -", "a b b,2")
        cases.step("order-kills", (code, sorts) == (1, {COUNTED}), out)
        code, sorts, out = sweep(box, "tail -1", "2")
        cases.step("order-ignored", (code, sorts) == (1, {PRINTED, COUNTED}), out)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

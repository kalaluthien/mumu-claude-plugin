#!/usr/bin/env python3
"""Run run-criteria.py `--hunks` on a temporary git repository whose change adds a script, under a check of a file git does not track and
a check that runs the script only inside a git checkout, as a fixture that skips its cases elsewhere does, and prints the greeting
outside one. Print `ok <case>` or `fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `git-check-swept`: the untracked check, which fails in a clone of the head and passes in the checkout, is named `not swept`, and the
  sweep judges the script's hunk and its mutants by the git-gated check, which runs the script there and kills them all, exit 0;
- `failing-check-stops`: a check that fails in the checkout too still stops the sweep with `fails at the head`, judging no hunk.

usage: replay-hunk-git-check.py"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
UNTRACKED = "1. [check] **The checkout holds its local file**: `test -f local.txt && echo ok` prints `ok`; on base nothing.\n"
TOOL = "2. [check] **The tool prints its greeting at the head**: `if git rev-parse --git-dir >/dev/null 2>&1; then python3 tool.py; else echo \"{text}\"; fi` prints `{text}`; on base nothing.\n"


def sweep(box, text):
    done = box.python(SCRIPT, "--hunks", "--ref", "main", replay_probe.write_text(box.work, "body.md", "## Definition of done\n\n" + UNTRACKED + TOOL.format(text=text)), timeout=300)
    return done.returncode, done.stdout + done.stderr


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("hunk-git-check-") as work:
        box = replay_probe.Sandbox(work)
        box.git("checkout", "-qb", "change")
        (box.repository / "tool.py").write_text('print("hello", 3)\n')
        box.git("add", "-A")
        (box.repository / "local.txt").write_text("kept out of git\n")
        box.git("commit", "-qm", "change")
        code, out = sweep(box, "hello 3")
        cases.step("git-check-swept", code == 0 and "1: not swept: it fails in a clone of the head and passes in the checkout" in out
                   and "fails at the head" not in out and "hunks: 1 reverted against main, 0 conditions made False, 2 mutants made, 0 unneeded" in out, out)
        code, out = sweep(box, "goodbye")
        cases.step("failing-check-stops", code == 1 and "2: fails at the head" in out and "hunks:" not in out, out)
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

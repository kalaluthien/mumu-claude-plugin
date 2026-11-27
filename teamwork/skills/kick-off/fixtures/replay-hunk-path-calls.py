#!/usr/bin/env python3
"""Run run-criteria.py `--hunks` on a temporary git repository whose change adds a script that refuses the name `..`, resolves its argument,
tests that it is a folder, prints what each other path call gives and prints three comparisons, with the checker under `fixtures/`, and edits the second line alone of a call an older script writes over two. Print `ok <case>` or
`fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `survivors-named`: a check that needs only the script's last line makes `--hunks` name, as surviving mutants with what each becomes, each of the eight path calls as its sibling, `resolve` at the line that names it in a call written over two, the older script's `resolve` too, and the equality with `".."` as a membership test, beside the unneeded refusal
  and the argument's index, exit 1; twenty mutants are made, none widening an inequality with a text, an equality with a number or one with a list, the script raising at its first line among them, which the check sees;
- `all-killed`: a check that runs the script on a folder, a link to it, a file, a folder whose name holds `..` and `..` itself, and the older script on the link, names none, exit 0;
- `siblings-only`: no sweep names `basename` or `isabs`, which have no sibling.

usage: replay-hunk-path-calls.py"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
BODY = "## Definition of done\n\n1. [check] **The checker prints ok for the change**: `python3 fixtures/check-tool.py {mode}` prints `ok`; on base nothing.\n"
TOOL = '''import os
import pathlib
import sys

target = pathlib.Path(sys.argv[1])
if target.name == "..":
    sys.exit("refused")
folder = (target
          .resolve())
print(folder.name if folder.is_dir() else "none")
print(os.path.basename(target), os.path.isabs(os.path.abspath(target)))
print(target.absolute().name, os.path.basename(os.path.realpath(target)), os.path.normpath(sys.argv[1]), target.is_file(), target.exists())
print(target.name != "", len(sys.argv) == 2, sys.argv[1:] == [str(target)])
print("ok")
'''
OLD = '''import pathlib
import sys

print(pathlib.Path(sys.argv[1])
      {})
'''
CHECKER = '''import subprocess
import sys


def run(name, script="tool.py"):
    done = subprocess.run([sys.executable, script, name], capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr


passed = run("real")[1].endswith("ok\\n") and run("plain.txt", "old.py") == (0, "plain.txt\\n")
if sys.argv[1] == "strong":
    passed = passed and run("real") == (0, "real\\nreal True\\nreal real real False True\\nTrue True True\\nok\\n") and run("link") == (0, "real\\nlink True\\nlink real link False True\\nTrue True True\\nok\\n")
    passed = passed and run("plain.txt") == (0, "none\\nplain.txt True\\nplain.txt plain.txt plain.txt True True\\nTrue True True\\nok\\n") and run("a..b") == (0, "a..b\\na..b True\\na..b a..b a..b False True\\nTrue True True\\nok\\n") and run("..") == (1, "refused\\n")
    passed = passed and run("link", "old.py") == (0, "real\\n")
print("ok" if passed else "no")
'''
LINE = "tool.py:{}: surviving mutant: no criterion fails when the {} becomes {}, so make a criterion fail on it or drop it"
SURVIVORS = {
    "old.py:5: surviving mutant: no criterion fails when the path call `resolve` becomes `absolute`, so make a criterion fail on it or drop it",
    "tool.py:6: unneeded condition: no criterion reaches this branch, so drop it or make a criterion refuse through it",
    LINE.format(5, "number `1`", "`0`"),
    LINE.format(6, 'equality `target.name == ".."`', "`'..' in target.name`"),
    LINE.format(9, "path call `resolve`", "`absolute`"),
    LINE.format(10, "path call `is_dir`", "`exists`"),
    LINE.format(11, "path call `abspath`", "`normpath`"),
    LINE.format(12, "path call `absolute`", "`resolve`"),
    LINE.format(12, "path call `realpath`", "`abspath`"),
    LINE.format(12, "path call `normpath`", "`abspath`"),
    LINE.format(12, "path call `is_file`", "`exists`"),
    LINE.format(12, "path call `exists`", "`is_dir`"),
    LINE.format(12, "number `1`", "`0`"),
    LINE.format(13, 'comparison `target.name != ""`', '`(not (target.name != ""))`'),
    LINE.format(13, "comparison `len(sys.argv) == 2`", "`(not (len(sys.argv) == 2))`"),
    LINE.format(13, "comparison `sys.argv[1:] == [str(target)]`", "`(not (sys.argv[1:] == [str(target)]))`"),
    LINE.format(13, "number `2`", "`0`"),
    LINE.format(13, "number `1`", "`0`"),
    LINE.format(13, "list `[str(target)]`", "`[]`"),
}


def sweep(box, mode):
    """(exit code, the summary's counts of conditions, mutants made and unneeded, the lines naming a finding, all it printed) of a `--hunks` sweep whose check runs in MODE."""
    done = box.python(SCRIPT, "--hunks", "--ref", "main", replay_probe.write_text(box.work, "body.md", BODY.format(mode=mode)), timeout=900)
    text = done.stdout + done.stderr
    summary = re.search(r"^hunks: 3 reverted against main, (\d+) conditions made False, (\d+) mutants made, (\d+) unneeded$", text, re.M)
    return done.returncode, summary and [int(count) for count in summary.groups()], {line for line in text.splitlines() if ": surviving mutant" in line or ": unneeded" in line}, text


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("hunk-path-calls-") as work:
        box = replay_probe.Sandbox(work, commit=False)
        for name in ("real", "a..b"):
            (box.repository / name).mkdir()
            (box.repository / name / "kept.txt").write_text("kept\n")
        (box.repository / "link").symlink_to("real")
        (box.repository / "plain.txt").write_text("plain\n")
        (box.repository / "old.py").write_text(OLD.format(".absolute().stem"))
        box.git("add", "-A")
        box.git("commit", "-qm", "base")
        box.git("checkout", "-qb", "change")
        (box.repository / "fixtures").mkdir()
        (box.repository / "tool.py").write_text(TOOL)
        (box.repository / "old.py").write_text(OLD.format(".resolve().name"))
        (box.repository / "fixtures" / "check-tool.py").write_text(CHECKER)
        box.git("add", "-A")
        box.git("commit", "-qm", "change")
        code, counts, weak, text = sweep(box, "weak")
        cases.step("survivors-named", (code, counts, weak) == (1, [1, 20, 19], SURVIVORS), text)
        code, counts, strong, text = sweep(box, "strong")
        cases.step("all-killed", (code, counts, strong) == (0, [1, 20, 0], set()), text)
        cases.step("siblings-only", len(weak) == len(SURVIVORS) and not any("basename" in line or "isabs" in line for line in weak | strong), sorted(weak | strong))
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

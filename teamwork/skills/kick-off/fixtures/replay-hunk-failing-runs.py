#!/usr/bin/env python3
"""Run run-criteria.py `--hunks` on a temporary git repository whose change edits one line of a script and leaves a second script alone,
with the checker under `fixtures/`; the edited script opens with a bare `#` line, which a raise put after its first byte would only lengthen, and holds an older line with a path call and an equality with a text. Print `ok <case>` or `fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `survivor-named`: a check that only finds two runs of the edited script equal makes `--hunks` name the script raising at its first line as
  a surviving mutant, beside the argument's index, exit 1; two mutants are made;
- `killed`: a check that reads what a run prints names none, two made, exit 0;
- `changed-files-only`: no sweep names the script the change left alone, and none makes a mutant of it, of the checker or of the older line.

usage: replay-hunk-failing-runs.py"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
BODY = "## Definition of done\n\n1. [check] **The checker prints ok for the change**: `python3 fixtures/check-tool.py {mode}` prints `ok`; on base nothing.\n"
TOOL = '''#
"""Print the first argument in capitals."""
import pathlib
import sys

KNOWN = pathlib.Path(sys.argv[0]).exists() or sys.argv[0] == "none"
print(sys.argv[1].upper(){})
'''
CHECKER = '''import pathlib
import subprocess
import sys


def run(script):
    return subprocess.run([sys.executable, script, "word"], capture_output=True, text=True).stdout


passed = run("tool.py") == run("tool.py") and "upper() +" in pathlib.Path("tool.py").read_text() and run("other.py") == "WORD\\n"
if sys.argv[1] == "strong":
    passed = passed and run("tool.py") == "WORD!\\n"
print("ok" if passed else "no")
'''
SURVIVORS = {
    "tool.py:1: surviving mutant: no criterion fails when the start of the file `` becomes `raise RuntimeError`, so make a criterion fail on it or drop it",
    "tool.py:7: surviving mutant: no criterion fails when the number `1` becomes `0`, so make a criterion fail on it or drop it",
}


def sweep(box, mode):
    """(exit code, the summary's counts of conditions, mutants made and unneeded, the lines naming a finding, all it printed) of a `--hunks` sweep whose check runs in MODE."""
    done = box.python(SCRIPT, "--hunks", "--ref", "main", replay_probe.write_text(box.work, "body.md", BODY.format(mode=mode)), timeout=900)
    text = done.stdout + done.stderr
    summary = re.search(r"^hunks: 2 reverted against main, (\d+) conditions made False, (\d+) mutants made, (\d+) unneeded$", text, re.M)
    return done.returncode, summary and [int(count) for count in summary.groups()], {line for line in text.splitlines() if ": surviving mutant" in line or ": unneeded" in line}, text


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("hunk-failing-runs-") as work:
        box = replay_probe.Sandbox(work, commit=False)
        for name in ("tool.py", "other.py"):
            (box.repository / name).write_text(TOOL.format(""))
        box.git("add", "-A")
        box.git("commit", "-qm", "base")
        box.git("checkout", "-qb", "change")
        (box.repository / "fixtures").mkdir()
        (box.repository / "tool.py").write_text(TOOL.format(' + "!"'))
        (box.repository / "fixtures" / "check-tool.py").write_text(CHECKER)
        box.git("add", "-A")
        box.git("commit", "-qm", "change")
        code, counts, weak, text = sweep(box, "weak")
        cases.step("survivor-named", (code, counts, weak) == (1, [0, 2, 2], SURVIVORS), text)
        code, counts, strong, text = sweep(box, "strong")
        cases.step("killed", (code, counts, strong) == (0, [0, 2, 0], set()), text)
        cases.step("changed-files-only", not any("other.py" in line or "fixtures/" in line for line in weak | strong), sorted(weak | strong))
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

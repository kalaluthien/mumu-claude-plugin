#!/usr/bin/env python3
"""Run run-criteria.py `--hunks` on a temporary git repository whose change has two hunks. Print `ok <case>` or
`fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `one-needed`: a sole check that needs only the first hunk, beside a score, makes `--hunks` name the second hunk's file and line and exit 1;
- `both-needed`: a check that needs both hunks makes it name none and exit 0;
- `table-same`: the call without `--hunks` prints the criteria table alone, its five columns and no hunk line;
- `line-in-needed-hunk`: a later commit deletes a Python file the check needs gone, adds a Python template that does not
  parse, and adds to a Python file with a condition of its own one hunk holding a print the sole check needs, a one-line refusal it does not and an `if` line inside a
  string, and a text file whose
  `if` line, valid Python, the check needs only to exist, and `--hunks` against the commit before names the refusal's line as an unneeded
  condition, not the hunk, the old condition, the string's line, the text file's line or the template, and exits 1;
- `condition-needed`: a check that runs through that refusal makes it name none, one mutant made, the refusal's number, not its test again, and exit 0;
- `mutant-survives`: a later commit adds to a Python file with a comparison and numbers of its own a line whose comparison and two numbers, one a float, set a bound, printed with a
  `True` flag, and an exit with 0, and a runner under `fixtures/` with an unused number that tries only a value far above the bound makes `--hunks` name
  each number of the bound as a surviving mutant and the 0 as made 1, not the comparison, the flag, the old line or the runner's number, and exit 1;
- `mutant-killed`: a check that also tries a value just below the bound and needs the exit makes it name none, five mutants made, the index of the
  argument among them, and exit 0;
- `first-break-stops`: of two checks, one that needs the first hunk, listed first, and one that counts its runs and prints an extra line when the second
  hunk is reverted, the second runs at the head and on the second revert only, and that revert counts as needed;
- `score-held-by-runner`: a task of one score, over a change to a Python file and the Python runner that replays it, to a text file and a new
  TypeScript runner that reads it, to a second text file, and adding a runner that fails and three Python files that pass but are no runner, a
  script, a helper under `fixtures/` and a `replay-` file in a `replay-` folder below it, makes `--hunks` hold the two passing runners, so it names the second
  text file's hunk, the failing runner's and each of the three files' as unneeded, not a failure at the head, makes two mutants that the runner kills,
  and exits 1.

usage: replay-hunk-revert.py"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
BODY = ("## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints ok; meets: the caller's need.\n\n"
        "## Definition of done\n\n1. [check] **The probe prints ok when it runs**: `{command}` prints `ok`; on base nothing.\n")
RUN_SECONDS = 600  # a `--hunks` call runs the checks once per revert


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with replay_probe.scratch("hunk-revert-") as folder:
        return replay(folder)


def replay(folder):
    cases = replay_probe.Cases()
    sandbox = replay_probe.Sandbox(folder, commit=False)
    work, git = sandbox.repository, sandbox.git

    git("init", "-q", "-b", "main")
    (work / "a.txt").write_text("old\n")
    (work / "b.txt").write_text("one\nold\n")
    git("add", ".")
    git("commit", "-q", "-m", "base")
    git("checkout", "-q", "-b", "change")
    (work / "a.txt").write_text("new\n")
    (work / "b.txt").write_text("one\nnew\n")
    git("commit", "-qam", "change")

    def call(command, *options, more=""):
        body = folder / "body.md"
        body.write_text(BODY.format(command=command) + more)
        done = sandbox.python(SCRIPT, *options, body, timeout=RUN_SECONDS)
        return done.returncode, done.stdout, done.stderr

    code, out, error = call("grep -q new a.txt && echo ok", "--hunks", "--ref", "main", more="2. [score] **The probe reads well**: sample: a.txt; rubric: yes 2, no 0.\n")
    cases.step("one-needed", code == 1 and "b.txt:2: unneeded hunk" in out and "a.txt" not in out.replace("hunks:", ""), (code, out, error))
    code, out, error = call("grep -q new a.txt && grep -q new b.txt && echo ok", "--hunks", "--ref", "main")
    cases.step("both-needed", code == 0 and "0 unneeded" in out and ": unneeded hunk" not in out, (code, out, error))
    code, out, error = call("grep -q new a.txt && echo ok")
    lines = out.splitlines()
    cases.step("table-same", code == 0 and lines[0].startswith("REPORTED: criteria at ") and lines[2] == "| # | criterion | result | output | sha-256 |"
         and lines[4].startswith("| 1 | The probe prints ok when it runs | pass | ok | ") and len(lines) == 5, (code, out, error))
    git("checkout", "-q", "-b", "lines")
    (work / "e.py").write_text("print('gone')\n")
    (work / "c.py").write_text("import sys\nif True: pass\nprint('old')\n")
    git("add", "e.py", "c.py")
    git("commit", "-qm", "kept")
    (work / "e.py").unlink()
    (work / "c.py").write_text("import sys\nif True: pass\nUSAGE = '''Run it.\nif the caller asks:\n'''\nif len(sys.argv) > 1: sys.exit('refused')\nprint('new')\n")
    (work / "d.txt").write_text("if ready: pass\n")
    (work / "g.py").write_text("def (:\nif ready: pass\n")
    git("add", "-A")
    git("commit", "-qm", "lines")
    code, out, error = call("python3 c.py | grep -q new && test -s d.txt && test -s g.py && test ! -e e.py && echo ok", "--hunks", "--ref", "lines~1")
    cases.step("line-in-needed-hunk", code == 1 and "c.py:6: unneeded condition" in out and "c.py:4" not in out and "c.py:2" not in out and "g.py" not in out and "unneeded hunk" not in out and "d.txt" not in out, (code, out, error))
    code, out, error = call("python3 c.py | grep -q new && test -s d.txt && test -s g.py && test ! -e e.py && python3 c.py x 2>&1 | grep -q refused && echo ok", "--hunks", "--ref", "lines~1")
    cases.step("condition-needed", code == 0 and "0 unneeded" in out and "1 conditions made False, 1 mutants made" in out, (code, out, error))
    git("checkout", "-q", "-b", "bound")
    (work / "h.py").write_text("import sys\nLIMIT = 7 if len(sys.argv) > 0 else 8\n")
    git("add", "h.py")
    git("commit", "-qm", "limit")
    (work / "h.py").write_text("import sys\nLIMIT = 7 if len(sys.argv) > 0 else 8\nprint('big' if int(sys.argv[1]) > 10 * 2.0 else 'small', flush=True)\nsys.exit(0)\n")
    (work / "fixtures").mkdir()
    (work / "fixtures" / "check-h.py").write_text("import subprocess, sys\nTRIES = 3\n"
                                                  "out = subprocess.run([sys.executable, 'h.py', sys.argv[1]], capture_output=True, text=True).stdout\n"
                                                  "sys.exit(0 if out == 'big\\n' else 1)\n")
    git("add", "h.py", "fixtures")
    git("commit", "-qm", "bound")
    code, out, error = call("python3 fixtures/check-h.py 30 && echo ok", "--hunks", "--ref", "bound~1")
    cases.step("mutant-survives", code == 1 and "h.py:3: surviving mutant: no criterion fails when the number `10` becomes `0`" in out
         and "the number `2.0` becomes `0`" in out and "h.py:4: surviving mutant: no criterion fails when the number `0` becomes `1`" in out
         and "comparison" not in out and "fixtures/" not in out and "h.py:2" not in out and "5 mutants made" in out, (code, out, error))
    code, out, error = call("python3 fixtures/check-h.py 30 && python3 h.py 15 > out.txt && grep -qx small out.txt && echo ok", "--hunks", "--ref", "bound~1")
    cases.step("mutant-killed", code == 0 and "0 unneeded" in out and "5 mutants made" in out, (code, out, error))
    git("checkout", "-q", "change")
    runs = folder / "runs"
    body = folder / "two.md"
    body.write_text(BODY.format(command="grep -q new a.txt && echo ok")
                    + f"2. [check] **The probe counts its runs**: `echo run >> {runs} && {{ grep -q new b.txt || echo old; }} && echo ok` prints `ok`; on base nothing.\n")
    done = sandbox.python(SCRIPT, "--hunks", "--ref", "main", body, timeout=RUN_SECONDS)
    count = runs.read_text().count("run") if runs.exists() else 0
    cases.step("first-break-stops", done.returncode == 0 and "0 unneeded" in done.stdout and count == 2, (done.returncode, count, done.stdout, done.stderr))
    git("checkout", "-q", "main")
    (work / "p" / "fixtures").mkdir(parents=True)
    replay = "import pathlib, subprocess, sys\nout = subprocess.run([sys.executable, str(pathlib.Path(__file__).parents[1] / 'tool.py')], capture_output=True, text=True).stdout\nsys.exit(0 if out == '{}\\n' else 1)\n"
    (work / "p" / "tool.py").write_text("import sys\nprint('old')\n")
    (work / "p" / "fixtures" / "replay-tool.py").write_text(replay.format("old"))
    (work / "p" / "notes.txt").write_text("old\n")
    (work / "p" / "other.txt").write_text("old\n")
    git("add", "-A")
    git("commit", "-qm", "tool")
    git("checkout", "-q", "-b", "scored")
    (work / "p" / "tool.py").write_text("import sys\nprint('new' if len(sys.argv) > 0 else 'none')\n")
    (work / "p" / "fixtures" / "replay-tool.py").write_text(replay.format("new"))
    (work / "p" / "notes.txt").write_text("new\n")
    (work / "p" / "other.txt").write_text("new\n")
    (work / "p" / "fixtures" / "replay-notes.ts").write_text("import { readFileSync } from \"fs\";\nprocess.exit(readFileSync(new URL(\"../notes.txt\", import.meta.url), \"utf8\") === \"new\\n\" ? 0 : 1);\n")
    (work / "p" / "fixtures" / "replay-broken.py").write_text("import sys\nsys.exit(1)\n")
    (work / "p" / "fixtures" / "replay-deep").mkdir()
    for file in ("lib.py", "fixtures/helper.py", "fixtures/replay-deep/replay-deep.py"):
        (work / "p" / file).write_text("print('here')\n")
    git("add", "-A")
    git("commit", "-qm", "scored")
    body.write_text(BODY.split("1. [check]")[0] + "1. [score] **The probe reads well**: sample: p/tool.py; rubric: yes 2, no 0.\n")
    done = sandbox.python(SCRIPT, "--hunks", "--ref", "scored~1", body, timeout=RUN_SECONDS)
    cases.step("score-held-by-runner", done.returncode == 1 and "p/other.txt:1: unneeded hunk" in done.stdout and "p/fixtures/replay-broken.py:1: unneeded hunk" in done.stdout
         and all(f"p/{file}:1: unneeded hunk" in done.stdout for file in ("lib.py", "fixtures/helper.py", "fixtures/replay-deep/replay-deep.py"))
         and "p/tool.py" not in done.stdout and "notes" not in done.stdout and "fails at the head" not in done.stdout and "2 mutants made, 5 unneeded" in done.stdout, (done.returncode, done.stdout, done.stderr))
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

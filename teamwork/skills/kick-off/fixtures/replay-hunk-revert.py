#!/usr/bin/env python3
"""Run run-criteria.py `--hunks` on a temporary git repository whose change has two hunks. Print `ok <case>` or
`fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `one-needed`: a sole check that needs only the first hunk makes `--hunks` name the second hunk's file and line and exit 1;
- `both-needed`: a check that needs both hunks makes it name none and exit 0;
- `table-same`: the call without `--hunks` prints the criteria table alone, its five columns and no hunk line.

usage: replay-hunk-revert.py"""
import os
import pathlib
import subprocess
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
BODY = ("## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints ok; meets: the caller's need.\n\n"
        "## Definition of done\n\n1. [check] **The probe prints ok when it runs**: `{command}` prints `ok`; on base nothing.\n")
failed = []


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {' '.join(str(detail).split())[:900]}", flush=True)
    if not ok:
        failed.append(name)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="hunk-revert-"))
    os.environ.update(HOME=str(work), GIT_AUTHOR_NAME="probe", GIT_AUTHOR_EMAIL="probe@example.com",
                      GIT_COMMITTER_NAME="probe", GIT_COMMITTER_EMAIL="probe@example.com")

    def git(*argv):
        subprocess.run(["git", *argv], cwd=work, check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    (work / "a.txt").write_text("old\n")
    (work / "b.txt").write_text("one\nold\n")
    git("add", ".")
    git("commit", "-q", "-m", "base")
    git("checkout", "-q", "-b", "change")
    (work / "a.txt").write_text("new\n")
    (work / "b.txt").write_text("one\nnew\n")
    git("commit", "-qam", "change")

    def call(command, *options):
        body = work.parent / f"{work.name}-body.md"
        body.write_text(BODY.format(command=command))
        done = subprocess.run([sys.executable, str(SCRIPT), *options, str(body)], cwd=work, capture_output=True, text=True)
        return done.returncode, done.stdout, done.stderr

    code, out, error = call("grep -q new a.txt && echo ok", "--hunks", "--ref", "main")
    step("one-needed", code == 1 and "b.txt:2: unneeded hunk" in out and "a.txt" not in out.replace("hunks:", ""), (code, out, error))
    code, out, error = call("grep -q new a.txt && grep -q new b.txt && echo ok", "--hunks", "--ref", "main")
    step("both-needed", code == 0 and "0 unneeded" in out and ": unneeded hunk" not in out, (code, out, error))
    code, out, error = call("grep -q new a.txt && echo ok")
    lines = out.splitlines()
    step("table-same", code == 0 and lines[0].startswith("REPORTED: criteria at ") and lines[2] == "| # | criterion | result | output | sha-256 |"
         and lines[4].startswith("| 1 | The probe prints ok when it runs | pass | ok | ") and len(lines) == 5, (code, out, error))
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

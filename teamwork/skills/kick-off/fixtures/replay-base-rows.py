#!/usr/bin/env python3
"""Run run-criteria.py `--base` on a temporary git repository whose base holds `old.py` and no `new.py`, on checks that quote `FAIL` on base. Print `ok <case>` or
`fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `new-python`: a check that runs a Python fixture the base lacks reads `base ok`;
- `new-shell`: the same for a shell script run by `bash`;
- `piped`: the same when the run is piped to `tail -1`;
- `present`: a fixture the base holds that prints another text is a `wrong base`;
- `mixed`: a missing fixture beside other output is a `wrong base`;
- `outside`: a missing file outside the export, which no change adds, is a `wrong base`.

usage: replay-base-rows.py"""
import os
import pathlib
import subprocess
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
BODY = ("## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints PASS; meets: the caller's need.\n\n"
        "## Definition of done\n\n1. [check] **The probe prints PASS when it runs**: `{command}` prints `PASS`; on base `{quote}`.\n")
# each case: the check, the quote, the row it must get
CASES = {"new-python": ("python3 new.py", "FAIL", "base ok"),
         "new-shell": ("bash new.sh", "FAIL", "base ok"),
         "piped": ("python3 new.py | tail -1", "FAIL", "base ok"),
         "present": ("python3 old.py", "FAIL", "wrong base"),
         "mixed": ("python3 old.py; python3 new.py", "FAIL", "wrong base"),
         "outside": ("python3 /nonexistent-folder/new.py", "FAIL", "wrong base")}


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="base-rows-"))
    os.environ.update(HOME=str(work), GIT_AUTHOR_NAME="probe", GIT_AUTHOR_EMAIL="probe@example.com", GIT_COMMITTER_NAME="probe", GIT_COMMITTER_EMAIL="probe@example.com")
    (work / "old.py").write_text("print('oops')\n")
    for argv in (["init", "-q", "-b", "main"], ["add", "."], ["commit", "-q", "-m", "base"]):
        subprocess.run(["git", *argv], cwd=work, check=True, capture_output=True)
    wrong = []
    for case, (command, quote, row) in CASES.items():
        body = work.parent / f"{work.name}-{case}.md"
        body.write_text(BODY.format(command=command, quote=quote))
        done = subprocess.run([sys.executable, str(SCRIPT), "--base", "--ref", "main", str(body)], cwd=work, capture_output=True, text=True)
        print(f"ok {case}" if f"| {row} |" in done.stdout else f"fail {case}: {' '.join((done.stdout + done.stderr).split())[:400]}", flush=True)
        wrong += [case] * (f"| {row} |" not in done.stdout)
    print("FAIL" if wrong else "PASS")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

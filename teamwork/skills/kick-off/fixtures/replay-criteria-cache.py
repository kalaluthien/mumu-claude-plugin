#!/usr/bin/env python3
"""Run run-criteria.py on a temporary git repository whose one `[check]` logs each run. Print `ok <case>` or `fail <case>: <detail>`
per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `same-files-once`: the call twice on the same files runs the check once, and the second table says one check was replayed;
- `other-worktree-once`: the call from a second worktree of the same files, which has another path, runs the check again, since its output may hold the path;
- `changed-file-runs`: a change to a file runs the check again;
- `fresh-runs`: `--fresh` on the same files runs it again;
- `failure-runs`: a check that fails runs on every call;
- `base-once`: `--base` twice runs the check once.

usage: replay-criteria-cache.py"""
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
    work = pathlib.Path(tempfile.mkdtemp(prefix="criteria-cache-"))
    log = work.parent / f"{work.name}-runs.log"
    os.environ.update(HOME=str(work), GIT_AUTHOR_NAME="probe", GIT_AUTHOR_EMAIL="probe@example.com",
                      GIT_COMMITTER_NAME="probe", GIT_COMMITTER_EMAIL="probe@example.com")

    def git(*argv, cwd=work):
        subprocess.run(["git", *argv], cwd=cwd, check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    (work / "a.txt").write_text("one\n")
    git("add", ".")
    git("commit", "-q", "-m", "base")

    def call(command, *options, cwd=work):
        log.write_text("")
        body = work.parent / f"{work.name}-body.md"
        body.write_text(BODY.format(command=command))
        done = subprocess.run([sys.executable, str(SCRIPT), *options, str(body)], cwd=cwd, capture_output=True, text=True)
        return done.stdout, done.stderr, len(log.read_text().split())

    passing = f"echo run >> {log}; grep -q one a.txt && echo ok"
    call(passing)
    out, error, runs = call(passing)
    step("same-files-once", runs == 0 and "cached: 1 checks replayed" in out and "| pass | ok |" in out, (runs, out, error))
    second = work.parent / f"{work.name}-second"
    git("worktree", "add", "-q", str(second), "-b", "second")
    out, error, runs = call(passing, cwd=second)
    step("other-worktree-once", runs == 1, (runs, out, error))
    (work / "a.txt").write_text("one two\n")
    out, error, runs = call(passing)
    step("changed-file-runs", runs == 1 and "cached" not in out, (runs, out, error))
    out, error, runs = call(passing, "--fresh")
    step("fresh-runs", runs == 1, (runs, out, error))
    failing = f"echo run >> {log}; grep -q absent a.txt && echo ok"
    call(failing)
    out, error, runs = call(failing)
    step("failure-runs", runs == 1 and "| fail |" in out, (runs, out, error))
    quoted = BODY.replace("on base nothing.", "on base `ok`.")
    body = work.parent / f"{work.name}-body.md"
    body.write_text(quoted.format(command=f"echo run >> {log}; echo ok"))
    log.write_text("")
    for _ in range(2):
        subprocess.run([sys.executable, str(SCRIPT), "--base", "--ref", "main", str(body)], cwd=work, capture_output=True, text=True)
    step("base-once", len(log.read_text().split()) == 1, log.read_text())
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Run run-criteria.py `--base` on a temporary git repository with a stand-in `claude`, on checks that all print `FAIL` on base. Print `ok <case>` or `fail <case>: <detail>`
per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `scan-named`: a grep of a file joined by `&&` to a run that prints the passing output on base is a `text scan` row, the call exits 1 and prints how to fix it;
- `pipe-kept`: a grep that reads what the system printed decides it, so the row is `base ok`;
- `system-kept`: a run that fails on base beside a grep is `base ok`;
- `value-kept`: a `test` of a value the system printed is `base ok`;
- `session-once`: a check that starts a session runs it once, with no second run to strip its scans.

usage: replay-text-scan.py"""
import os
import pathlib
import subprocess
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
BODY = ("## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints PASS; meets: the caller's need.\n\n"
        "## Definition of done\n\n1. [check] **The probe prints PASS when it runs**: `{command}` prints `PASS`; on base `FAIL`.\n")
results = {}


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {' '.join(str(detail).split())[:900]}", flush=True)
    results[name] = ok


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="text-scan-"))
    log = work.parent / f"{work.name}-sessions.log"
    stand_in = work.parent / f"{work.name}-bin"
    stand_in.mkdir()
    (stand_in / "claude").write_text(f"#!/bin/sh\necho session >> {log}\n")
    (stand_in / "claude").chmod(0o755)
    os.environ.update(HOME=str(work), PATH=f"{stand_in}{os.pathsep}{os.environ['PATH']}", GIT_AUTHOR_NAME="probe", GIT_AUTHOR_EMAIL="probe@example.com",
                      GIT_COMMITTER_NAME="probe", GIT_COMMITTER_EMAIL="probe@example.com")
    (work / "README.md").write_text("hello\n")
    (work / "tool.py").write_text("print('ok')\n")
    for argv in (["init", "-q", "-b", "main"], ["add", "."], ["commit", "-q", "-m", "base"]):
        subprocess.run(["git", *argv], cwd=work, check=True, capture_output=True)

    def call(command):
        log.write_text("")
        body = work.parent / f"{work.name}-body.md"
        body.write_text(BODY.format(command=command))
        done = subprocess.run([sys.executable, str(SCRIPT), "--base", "--ref", "main", str(body)], cwd=work, capture_output=True, text=True)
        return done.returncode, done.stdout, done.stderr, len(log.read_text().split())

    code, out, error, _ = call("grep -q zzzq README.md && python3 tool.py >/dev/null && echo PASS || echo FAIL")
    step("scan-named", code == 1 and "| text scan |" in out and "To fix a `text scan` row" in out, (code, out, error))
    code, out, error, _ = call("python3 tool.py 2>/dev/null | grep -q zzzq && echo PASS || echo FAIL")
    step("pipe-kept", code == 0 and "| base ok |" in out, (code, out, error))
    code, out, error, _ = call("grep -q hello README.md && python3 missing.py 2>/dev/null && echo PASS || echo FAIL")
    step("system-kept", code == 0 and "| base ok |" in out, (code, out, error))
    code, out, error, _ = call("a=$(python3 tool.py | grep -c zzzq); test \"$a\" = 1 && echo PASS || echo FAIL")
    step("value-kept", code == 0 and "| base ok |" in out, (code, out, error))
    code, out, error, sessions = call("claude -p hi >/dev/null; grep -q zzzq README.md && echo PASS || echo FAIL")
    step("session-once", code == 0 and "| base ok |" in out and sessions == 1, (code, sessions, out, error))
    print("PASS" if all(results.values()) else "FAIL")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

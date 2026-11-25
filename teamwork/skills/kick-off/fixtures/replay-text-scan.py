#!/usr/bin/env python3
"""Run run-criteria.py `--base` on a temporary git repository with a stand-in `claude`, on checks that all print `FAIL` on base. Print `ok <case>` or `fail <case>: <detail>`
per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `scan-named`: a grep of a file joined by `&&` to a run that prints the passing output on base is a `text scan` row, the call exits 1 and prints how to fix it;
- `pipe-kept`: a grep that reads what the system printed decides it, so the row is `base ok`;
- `system-kept`: a run that fails on base beside a grep is `base ok`;
- `value-kept`: a `test` of a value the system printed is `base ok`;
- `written-kept`: a grep of a file the run wrote is `base ok`, since it judges the system;
- `session-once`: a check that starts a session runs it once, with no second run to strip its scans.

usage: replay-text-scan.py"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("text-scan-") as work:
        sandbox = replay_probe.Sandbox(work, commit=False)
        log = work / "sessions.log"
        replay_probe.write_text(sandbox.bin, "claude", f"#!/bin/sh\necho session >> '{log}'\n").chmod(0o755)
        replay_probe.write_text(sandbox.repository, "README.md", "hello\n")
        replay_probe.write_text(sandbox.repository, "tool.py", "print('ok')\n")
        sandbox.git("add", ".")
        sandbox.git("commit", "-q", "-m", "base")

        def call(command):
            log.write_text("")
            body = replay_probe.write_text(work, "body.md", replay_probe.BODY.replace("`basename PASS`", f"`{command}`"))
            done = sandbox.python(SCRIPT, "--base", "--ref", "main", body)
            return done.returncode, done.stdout, done.stderr, len(log.read_text().split())

        code, out, error, _ = call("grep -q zzzq README.md && python3 tool.py >/dev/null && echo PASS || echo FAIL")
        cases.step("scan-named", code == 1 and "| text scan |" in out and "To fix a `text scan` row" in out, (code, out, error))
        code, out, error, _ = call("python3 tool.py 2>/dev/null | grep -q zzzq && echo PASS || echo FAIL")
        cases.step("pipe-kept", code == 0 and "| base ok |" in out, (code, out, error))
        code, out, error, _ = call("grep -q hello README.md && python3 missing.py 2>/dev/null && echo PASS || echo FAIL")
        cases.step("system-kept", code == 0 and "| base ok |" in out, (code, out, error))
        code, out, error, _ = call("a=$(python3 tool.py | grep -c zzzq); test \"$a\" = 1 && echo PASS || echo FAIL")
        cases.step("value-kept", code == 0 and "| base ok |" in out, (code, out, error))
        code, out, error, _ = call("python3 tool.py > made.txt; grep -q zzzq made.txt && echo PASS || echo FAIL")
        cases.step("written-kept", code == 0 and "| base ok |" in out, (code, out, error))
        code, out, error, sessions = call("claude -p hi >/dev/null; grep -q zzzq README.md && echo PASS || echo FAIL")
        cases.step("session-once", code == 0 and "| base ok |" in out and sessions == 1, (code, sessions, out, error))
    return cases.finish()

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Check that run-criteria.py runs a check with its standard input closed, though its own standard input is an open pipe nobody writes to, and print `ok <case>` or
`fail <case>: <what it saw>`, then `PASS check stdin` or `FAIL check stdin`; exit 1 on any failure:
- `closed`: a check that reads its standard input to the end exits 0 and prints its `PASS` within the limit, where an open input would hold it until the limit.

usage: replay-check-stdin.py"""
import pathlib
import subprocess
import sys

SKILL = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL.parents[1] / "lib"))
import replay_probe  # noqa: E402

RUN = SKILL / "scripts" / "run-criteria.py"
LIMIT = 10
CODE = (f"import importlib.util, sys; spec = importlib.util.spec_from_file_location('run_criteria', {str(RUN)!r}); module = importlib.util.module_from_spec(spec); "
        f"spec.loader.exec_module(module); module.run_limit = {LIMIT * 4}; print(module.run('cat >/dev/null; echo PASS', sys.argv[1], {LIMIT}))")


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases("check stdin")
    with replay_probe.scratch("check-stdin-") as work:  # a check's folder under the temp folder is searched for strays, which this runner must not be
        return run(cases, work)


def run(cases, work):
    holder = subprocess.Popen([sys.executable, "-c", CODE, str(work)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)  # the pipe stays open until this call ends
    try:
        out = holder.stdout.readline()
    finally:
        holder.kill()
        err = holder.stderr.read()
        holder.wait()
    cases.step("closed", out.strip() == "(0, 'PASS')", [out, err])
    return cases.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

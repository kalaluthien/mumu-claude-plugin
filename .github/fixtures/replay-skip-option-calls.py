#!/usr/bin/env python3
"""Run `.github/check-repository.py` on a folder holding a plugin whose `fixtures/replay-option-calls.py` logs each run, and print `ok <case>` or
`fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `skipped`: `--skip-fixtures` runs the option replay no time, since it is a fixture runner and a runner that checks a copy of the repository would start it again;
- `run`: a call without the flag runs it once.

usage: replay-skip-option-calls.py"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

GITHUB = pathlib.Path(__file__).resolve().parents[1]
OPTION_REPLAY = "import os, pathlib\npathlib.Path(os.environ['OPTION_LOG']).open('a').write('run\\n')\nprint('0 scripts, 0 calls, 0 not answered')\n"


def runs(root, log, *flags):
    log.write_text("")
    subprocess.run([sys.executable, str(root / ".github" / "check-repository.py"), *flags, str(root)], capture_output=True, text=True, env={**os.environ, "OPTION_LOG": str(log)})
    return log.read_text().count("run")


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    holds = True
    with tempfile.TemporaryDirectory() as work:
        root = pathlib.Path(work) / "root"
        shutil.copytree(GITHUB, root / ".github", ignore=shutil.ignore_patterns("fixtures", "__pycache__"))
        (root / "plugin" / "fixtures").mkdir(parents=True)
        (root / "plugin" / "fixtures" / "replay-option-calls.py").write_text(OPTION_REPLAY)
        log = pathlib.Path(work) / "log"
        for case, flags, want in (("skipped", ("--skip-fixtures",), 0), ("run", (), 1)):
            got = runs(root, log, *flags)
            holds = holds and got == want
            print(f"ok {case}" if got == want else f"fail {case}: the option replay ran {got} times, not {want}")
    print("PASS" if holds else "FAIL")
    return 0 if holds else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

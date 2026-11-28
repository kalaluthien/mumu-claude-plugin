#!/usr/bin/env python3
"""Run run-criteria.py `--base` on a temporary git repository whose base holds `old.py` and no `new.py`, on checks that quote `FAIL` on base. Print `ok <case>` or
`fail <case>: <detail>` per case, then `PASS` or `FAIL`, and exit 1 on any failure:
- `new-python`: a check that runs a Python fixture the base lacks reads `base ok`;
- `new-shell`: the same for a shell script run by `bash`;
- `new-bun`: the same for a TypeScript fixture run by `bun`;
- `piped`: the same when the run is piped to `tail -1`;
- `present`: a fixture the base holds that prints another text is a `wrong base`;
- `mixed`: a missing fixture beside other output is a `wrong base`;
- `read`: a read of a missing file, which a text scan names no more than a run, is a `wrong base`;
- `quoted-error`: a missing script whose own error is quoted reads `base ok`;
- `outside`: a missing file outside the export, which no change adds, is a `wrong base`.

usage: replay-base-rows.py"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
BODY = ("## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints PASS; meets: the caller's need.\n\n"
        "## Definition of done\n\n1. [check] **The probe prints PASS when it runs**: `{command}` prints `PASS`; on base `{quote}`.\n")
# each case: the check, the quote, the row it must get
CASES = {"new-python": ("python3 new.py", "FAIL", "base ok"),
         "new-shell": ("bash new.sh", "FAIL", "base ok"),
         "new-bun": ("bun new.ts", "FAIL", "base ok"),
         "piped": ("python3 new.py | tail -1", "FAIL", "base ok"),
         "present": ("python3 old.py", "FAIL", "wrong base"),
         "mixed": ("python3 old.py; python3 new.py", "FAIL", "wrong base"),
         "read": ("grep foo new.py | tail -1", "FAIL", "wrong base"),
         "quoted-error": ("bash new.sh", "bash: new.sh: No such file or directory", "base ok"),
         "outside": ("python3 /nonexistent-folder/new.py", "FAIL", "wrong base")}


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    cases = replay_probe.Cases()
    with replay_probe.scratch("base-rows-") as work:
        box = replay_probe.Sandbox(work, commit=False)
        replay_probe.write_text(box.repository, "old.py", "print('oops')\n")
        box.git("add", ".")
        box.git("commit", "-q", "-m", "base")
        for case, (command, quote, row) in CASES.items():
            done = box.python(SCRIPT, "--base", "--ref", "main", replay_probe.write_text(work, f"{case}.md", BODY.format(command=command, quote=quote)))
            cases.step(case, f"| {row} |" in done.stdout, done.stdout + done.stderr)
    return cases.finish()

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

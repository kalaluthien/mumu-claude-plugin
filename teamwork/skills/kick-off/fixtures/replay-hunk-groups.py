#!/usr/bin/env python3
"""Run run-criteria.py `--hunks` on a temporary git repository whose change holds a 30-hunk file that every revert breaks, a
3-hunk file with an unneeded hunk beside two needed ones, a 30-hunk file no check reads, an 8-hunk file whose second half is needed, a deleted file and a Python file whose added refusal no check reaches. Print `ok <case>` or `fail <case>: <detail>` per case, then `PASS` or
`FAIL`, and exit 1 on any failure:
- `few-runs`: the check ran at most 3 times with the big file reverted in part or whole;
- `names-unneeded`: the unneeded hunk's line and the unreached refusal's line are named, no line of the big file or the deleted file is, and the call exits 1;
- `names-whole`: every hunk of the unread file is named, since reverting them together passes;
- `names-half`: the first four hunks of the half-needed file are named and the line says four are not judged one by one;
- `each-judges-all`: with `--each` the check ran once per hunk of the big file.

usage: replay-hunk-groups.py"""
import os
import pathlib
import subprocess
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
BODY = ("## Goal\n\nThe probe has a flow.\n\nPath: caller: a probe; before: nothing prints; after: it prints ok; meets: the caller's need.\n\n"
        "## Definition of done\n\n1. [check] **The probe prints ok when it runs**: `{command}` prints `ok`; on base nothing.\n")
HUNKS = 30
results = {}


def step(name, ok, detail=""):
    print(f"ok {name}" if ok else f"fail {name}: {' '.join(str(detail).split())[:900]}", flush=True)
    results[name] = ok


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    work = pathlib.Path(tempfile.mkdtemp(prefix="hunk-groups-"))
    log = work.parent / f"{work.name}-runs.log"
    os.environ.update(HOME=str(work), GIT_AUTHOR_NAME="probe", GIT_AUTHOR_EMAIL="probe@example.com",
                      GIT_COMMITTER_NAME="probe", GIT_COMMITTER_EMAIL="probe@example.com")

    def git(*argv):
        subprocess.run(["git", *argv], cwd=work, check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    (work / "big.txt").write_text("".join(f"old {n}\nkeep {n}\n" for n in range(HUNKS)))
    (work / "small.txt").write_text("a old\nkeep\nb old\nkeep\nc old\n")
    (work / "gone.txt").write_text("here\n")
    (work / "wide.txt").write_text("".join(f"old {n}\nkeep {n}\n" for n in range(HUNKS)))
    (work / "half.txt").write_text("".join(f"old {n}\nkeep {n}\n" for n in range(8)))
    (work / "c.py").write_text("import sys\nprint('old')\n")
    git("add", ".")
    git("commit", "-q", "-m", "base")
    git("checkout", "-q", "-b", "change")
    (work / "big.txt").write_text("".join(f"new {n}\nkeep {n}\n" for n in range(HUNKS)))
    (work / "small.txt").write_text("a new\nkeep\nb new\nkeep\nc new\n")
    (work / "gone.txt").unlink()
    (work / "wide.txt").write_text("".join(f"new {n}\nkeep {n}\n" for n in range(HUNKS)))
    (work / "half.txt").write_text("".join(f"new {n}\nkeep {n}\n" for n in range(8)))
    (work / "c.py").write_text("import sys\nif len(sys.argv) > 1: sys.exit('refused')\nprint('new')\n")
    git("commit", "-qam", "change")
    # a run that leaves a line in the log is one where the big file is not whole, so a reverted run; the unneeded hunk is the middle one of small.txt
    command = (f"test $(grep -c '^new' big.txt) = {HUNKS} || echo big >> {log}; "
               f"test $(grep -c '^new' big.txt) = {HUNKS} && test $(grep -c '^new [4-7]$' half.txt) = 4 && grep -q '^a new' small.txt && grep -q '^c new' small.txt && test ! -e gone.txt && python3 c.py | grep -q new && echo ok")
    body = work.parent / f"{work.name}-body.md"
    body.write_text(BODY.format(command=command))

    def call(*options):
        log.write_text("")
        done = subprocess.run([sys.executable, str(SCRIPT), "--hunks", "--ref", "main", *options, str(body)], cwd=work, capture_output=True, text=True)
        return done.returncode, done.stdout, done.stderr, len(log.read_text().split())

    code, out, error, runs = call()
    step("few-runs", runs <= 3 and "big.txt: 30 hunks not judged one by one" in out, (runs, out, error))
    step("names-unneeded", code == 1 and "small.txt:3: unneeded hunk" in out and "big.txt:" not in out.replace("big.txt: ", "") and "c.py:2: unneeded condition" in out and "small.txt:1" not in out and "small.txt:5" not in out and "gone.txt" not in out, (code, out, error))
    step("names-whole", all(f"wide.txt:{2 * n + 1}: unneeded hunk" in out for n in range(HUNKS)), (code, out, error))
    step("names-half", all(f"half.txt:{2 * n + 1}: unneeded hunk" in out for n in range(4)) and "half.txt:9" not in out and "half.txt: 4 hunks not judged one by one" in out, (code, out, error))
    code, out, error, runs = call("--each")
    step("each-judges-all", runs == HUNKS and "small.txt:3: unneeded hunk" in out, (runs, code, out, error))
    print("PASS" if all(results.values()) else "FAIL")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

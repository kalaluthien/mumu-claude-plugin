#!/usr/bin/env python3
"""Check that `run-criteria.py`'s `take_back` puts every hunk of a random edit back, so the file equals its base byte for byte: 400
random pairs of files whose lines hold form feeds, carriage returns, trailing spaces and empty lines, with or without a final newline,
are diffed by `git diff -U0` and taken back. Print `ok <case>` or `fail <case>: <detail>` per failing pair, then `PASS` or `FAIL`,
and exit 1 on any failure.

usage: replay-take-back.py"""
import importlib.util
import pathlib
import random
import subprocess
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run-criteria.py"
PIECES = ["a", "b", "", "x\x0cy", "t  ", "c\r", "d\x0bx", "e\x85", "same", "-dash", "+plus", "@@ at", "\\ slash"]
CASES = 400
results = {}


def step(name, ok, detail=""):
    if not ok:
        print(f"fail {name}: {detail}"[:900], flush=True)
    results[name] = ok


def lines(generator):
    body = [generator.choice(PIECES) for _ in range(generator.randint(0, 9))]
    return "".join(piece + "\n" for piece in body[:-1]) + "".join(piece + generator.choice(["", "\n"]) for piece in body[-1:])


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    spec = importlib.util.spec_from_file_location("run_criteria", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parents[3] / "lib"))
    spec.loader.exec_module(module)
    generator = random.Random(1450)
    work = pathlib.Path(tempfile.mkdtemp(prefix="take-back-"))
    for name in ("old", "new"):
        (work / name).mkdir()
    for number in range(CASES):
        base, head = lines(generator), lines(generator)
        (work / "old" / "f").write_bytes(base.encode("latin-1"))
        (work / "new" / "f").write_bytes(head.encode("latin-1"))
        diff = subprocess.run(["git", "diff", "--no-index", "-U0", "--src-prefix=a/", "--dst-prefix=b/", "old/f", "new/f"], cwd=work, capture_output=True).stdout
        patches = [patch for _, _, patch in module.split_hunks(diff.decode("latin-1"))]
        step(f"pair-{number}", module.take_back(head, patches) == base, (repr(base), repr(head)))
    print("PASS" if all(results.values()) else "FAIL")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

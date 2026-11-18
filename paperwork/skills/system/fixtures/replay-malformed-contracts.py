#!/usr/bin/env python3
"""Replay the checker on malformed copies of the parcel-locker contract and fail when one makes it crash.

usage: replay-malformed-contracts.py

Each of 200 copies has one value, at any depth, removed or replaced by a value of another shape, chosen by a fixed seed. The checker must answer each
with exit status 0 or 1 and no traceback, since a writer mends a contract from `where: rule: message` lines. It prints each crash, then PASS or FAIL."""
import concurrent.futures
import copy
import json
import pathlib
import random
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
CHECK = HERE.parent / "scripts" / "check-contract.py"
GONE = object()
SHAPES = (GONE, None, 5, "x", "", True, [], {}, [1], [[1]], {"a": 1}, ["x"], [{}])


def places(value, path=()):
    """The path of every value inside VALUE."""
    children = value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else ()
    for key, child in children:
        yield path + (key,)
        yield from places(child, path + (key,))


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    contract = json.loads((HERE / "parcel-locker.json").read_text())
    paths = list(places(contract))
    chooser = random.Random(1386)
    cases = []
    for copied in [{}, [], "x"] + [copy.deepcopy(contract) for _ in range(200)]:
        path, shape = chooser.choice(paths), chooser.choice(SHAPES)
        holder = copied
        for key in path[:-1] if isinstance(copied, dict) and copied else ():
            holder = holder[key]
        if isinstance(copied, dict) and copied and shape is GONE:
            del holder[path[-1]]
        elif isinstance(copied, dict) and copied:
            holder[path[-1]] = shape
        cases.append((copied, path, shape))

    def crashed(case):
        copied, path, shape = case
        with tempfile.TemporaryDirectory() as folder:
            target = pathlib.Path(folder) / "contract.json"
            target.write_text(json.dumps(copied))
            done = [(call, subprocess.run([sys.executable, str(CHECK), call, str(target)], capture_output=True, text=True)) for call in ("check", "read", "gaps")]
        return [f"FAIL {call} crashes with {'nothing' if shape is GONE else json.dumps(shape)} at {'/'.join(map(str, path))}"
                for call, one in done if one.returncode not in (0, 1) or "Traceback" in one.stderr]

    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        crashes = [line for lines in pool.map(crashed, cases) for line in lines]
    print("\n".join(crashes + ["FAIL" if crashes else "PASS"]))
    return 1 if crashes else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Replay check-contract.py on contracts nested past Python's depth, which it must refuse in one line rather than a traceback.

usage: replay-deep-contract.py

It writes a file of 100000 nested lists, and the interaction fixture with a `layout` tree 3000 entries deep, and runs `check` and `order`
on each: each run must exit 1 and print one line on stderr naming the file, and no traceback. It prints `FAIL <file> <call>: <reason>` per
miss, then PASS or FAIL; exit 1 on a miss."""
import json
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
CHECKER = HERE.parent / "scripts" / "check-contract.py"
DEPTH = 100000
TREE = 3000


def deep_tree():
    """The interaction fixture, its name store's `layout` a tree TREE entries deep."""
    contract = json.loads((HERE / "name-lookup.json").read_text())
    tree = [{"name": "leaf"}]
    for k in range(TREE):
        tree = [{"name": f"folder-{k}", "children": tree}]
    next(node for node in contract["nodes"] if node["id"] == "name-store").setdefault("info", {})["layout"] = tree
    return json.dumps(contract)


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    missed = 0
    with tempfile.TemporaryDirectory() as folder:
        files = {"nested.json": "[" * DEPTH + "]" * DEPTH, "deep-tree.json": deep_tree()}
        for name, text in files.items():
            path = pathlib.Path(folder) / name
            path.write_text(text)
            for call in ("check", "order"):
                run = subprocess.run([sys.executable, str(CHECKER), call, str(path)], capture_output=True, text=True)
                lines = run.stderr.strip().splitlines()
                if run.returncode != 1 or len(lines) != 1 or not lines[0].startswith(f"{path}: ") or "Traceback" in run.stderr:
                    missed += 1
                    print(f"FAIL {name} {call}: exit {run.returncode}, stderr {run.stderr.strip()[-200:]!r}")
    print("FAIL" if missed else "PASS")
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

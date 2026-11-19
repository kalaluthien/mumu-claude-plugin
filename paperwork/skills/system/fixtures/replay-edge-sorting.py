#!/usr/bin/env python3
"""Replay the edge sorting on a copy of each example's sources and fail when a changed file does not change what is reported.

usage: replay-edge-sorting.py

The sources that the nodes of each `../examples/*/contract.json` name are copied from the repository's root and sorted there. An import of
an unrelated node's file must then report one absent relation more, and a removed file must print its `missing path` line and exit 1.
It prints one PASS or FAIL line per example with its counts, then PASS or FAIL."""
import itertools
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[4]
SORT = HERE.parent / "scripts" / "sort-edges.py"


def sorted_under(path, root):
    """The exit status, the three counts and the output of the sorting call on the contract at PATH under ROOT."""
    done = subprocess.run([sys.executable, str(SORT), str(path), "--root", str(root)], capture_output=True, text=True)
    counts = {kind: int(count) for kind, count in re.findall(r"^(convergent|divergent|absent) (\d+):", done.stdout, re.MULTILINE)}
    return done.returncode, counts, done.stdout


def faults(path):
    """What the sorting call gets wrong on the example at PATH and its two changed copies, then the line of its counts."""
    contract = json.loads(path.read_text())
    sources = {source["id"]: source["path"] for source in contract["sources"]}
    nodes = {node["id"]: node["files"] for node in contract["nodes"] if node.get("files")}
    with tempfile.TemporaryDirectory() as folder:
        root = pathlib.Path(folder)
        for name in {name for files in nodes.values() for name in files}:
            (root / sources[name]).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / sources[name], root / sources[name])
        status, counts, printed = sorted_under(path, root)
        if status != 0 or len(counts) != 3:
            return [f"the sorting call exits {status} and prints {len(counts)} counts"], ""
        apart = next((pair for pair in itertools.combinations(sorted(nodes), 2) if f"{pair[0]} and {pair[1]}: " not in printed and not set(nodes[pair[0]]) & set(nodes[pair[1]])), None)
        found = []
        if apart is None:
            found.append("no two mapped nodes are without a relation, so no import can add one")
        else:
            importer, imported = root / sources[nodes[apart[0]][0]], pathlib.Path(sources[nodes[apart[1]][0]])
            kept = importer.read_text()
            importer.write_text(kept + f"\nimport {imported.name}\n")
            _, changed, _ = sorted_under(path, root)
            importer.write_text(kept)
            if changed != {**counts, "absent": counts["absent"] + 1}:
                found.append(f"an import of {imported.name} in {importer.name} gives {changed}, expected one absent more than {counts}")
        gone = sources[next(iter(nodes.values()))[0]]
        (root / gone).unlink()
        status, _, printed = sorted_under(path, root)
        if status != 1 or f": {gone}\n" not in printed or "missing path " not in printed:
            found.append(f"a removed {gone} is not reported as a missing path, exit {status}")
    return found, ", ".join(f"{kind} {count}" for kind, count in counts.items())


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    failed = 0
    examples = sorted((HERE.parent / "examples").glob("*/contract.json"))
    for path in examples:
        found, counts = faults(path)
        failed += bool(found)
        print(f"FAIL {path.parent.name}: {'; '.join(found)}" if found else f"PASS {path.parent.name}: {counts}")
    if not examples:
        failed += 1
        print("FAIL no example contract to sort")
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

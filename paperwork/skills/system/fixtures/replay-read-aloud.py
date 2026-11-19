#!/usr/bin/env python3
"""Replay the checker's `read` call on each example contract and fail when a line is not read in its order.

usage: replay-read-aloud.py

For each `../examples/*/contract.json` the output must hold a `sentence:` line per static edge, a `transition:` line per transition, an
`opens:` and an `opened by:` line per node that opens a level, and each property's statement at the end of a line. It prints one PASS or
FAIL line per example, then PASS or FAIL."""
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from contract_levels import nested  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
CHECK = HERE.parent / "scripts" / "check-contract.py"


def expected(contract):
    """The lines `read` must print for CONTRACT."""
    labels = {element["id"]: element["label"] for level in contract["levels"] for kind in ("areas", "nodes", "edges") for element in level.get(kind, [])}
    titles = {level["id"]: level["title"] for level in contract["levels"]}

    def shown(text):
        def label(match):
            found = labels.get(match.group(1), match.group(0))
            return found[:1].upper() + found[1:] if match.start() == 0 or text[:match.start()].endswith(". ") else found
        return re.sub(r"\{([a-z0-9-]+)\}", label, text)

    lines = []
    for level in contract["levels"]:
        for node in level["nodes"]:
            if "opens" in node:
                lines += [f"  opens: {node['label']} -> {node['opens']}", f"  opened by: {node['label']} ({titles[level['id']]})"]
        for edge in level.get("edges", []):
            start, end, info = labels[edge["from"]], labels[edge["to"]], edge.get("info", {})
            if edge["tag"] == "transition":
                guard = f" [{shown(info['guard'])}]" if "guard" in info else ""
                action = f" / {shown(info['action'])}" if "action" in info else ""
                lines.append(f"  transition: {start} -- {shown(edge['label'])}{guard}{action} --> {end}")
            else:
                lines.append(f"  sentence: {start} {shown(edge['label'])} {'each of ' if edge.get('many') else ''}{end}.")
    return lines, [shown(item["statement"]) for item in contract.get("properties", [])]


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    failed = 0
    examples = sorted((HERE.parent / "examples").glob("*/contract.json"))
    for path in examples:
        printed = subprocess.run([sys.executable, str(CHECK), "read", str(path)], capture_output=True, text=True).stdout.splitlines()
        lines, statements = expected(nested(json.loads(path.read_text())))
        missing = [line for line in lines if line not in printed] + [text for text in statements if not any(line.endswith(": " + text) for line in printed)]
        failed += bool(missing)
        print(f"FAIL {path.parent.name}: {len(missing)} lines not read, the first: {missing[0]}" if missing else f"PASS {path.parent.name}: {len(lines) + len(statements)} lines read in order")
    if not examples:
        failed += 1
        print("FAIL no example contract to read")
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

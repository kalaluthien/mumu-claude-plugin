#!/usr/bin/env python3
"""Print `PASS tier order` when the tier table of the agent adapter runs `light`, `mid`, `deep`, `open` with no effort column and
the manager's Swap up names every tier below `open`, else `FAIL: <what differed>`.

usage: replay-tier-order.py"""
import pathlib
import re
import sys

REFERENCES = pathlib.Path(__file__).resolve().parents[1] / "references"
ORDER = ["light", "mid", "deep", "open"]


def main(args):
    if args:
        sys.stderr.write(__doc__ + "\n")
        return 2
    adapter = (REFERENCES / "adapters" / "agent-claude.md").read_text()
    section = adapter.split("## Tier of a worker")[1].split("\n## ")[0]
    header = re.search(r"^\| tier \|.*$", section, re.M)
    rows = re.findall(r"^\| `(\w+)` \|", section, re.M)
    if not header or "effort" in header.group(0):
        print("FAIL: tier table missing or has an effort column")
    elif rows != ORDER:
        print(f"FAIL: rows run {rows}, not {ORDER}")
    else:
        swap = re.search(r"\*\*Swap up\*\*: a `BLOCKED:` of an? ([^\n]*?) worker", (REFERENCES / "manager.md").read_text())
        named = re.findall(r"`(\w+)`", swap.group(1)) if swap else []
        if named != ORDER[:-1]:
            print(f"FAIL: Swap up names {named}, not {ORDER[:-1]}")
        else:
            print("PASS tier order")
    return 0


sys.exit(main(sys.argv[1:]))

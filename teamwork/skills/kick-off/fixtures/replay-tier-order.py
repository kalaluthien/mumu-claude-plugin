#!/usr/bin/env python3
"""Print `PASS tier order` when the tier table of the agent adapter runs `light`, `mid`, `deep`, `open` with no effort column and
the manager's Swap up names every tier below `open`, else `FAIL: <what differed>` and exit 1.

usage: replay-tier-order.py"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import replay_probe  # noqa: E402

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
        return replay_probe.fail("tier table missing or has an effort column")
    if rows != ORDER:
        return replay_probe.fail(f"rows run {rows}, not {ORDER}")
    swap = re.search(r"\*\*Swap up\*\*: a `BLOCKED:` of an? ([^\n]*?) worker", (REFERENCES / "manager.md").read_text())
    named = re.findall(r"`(\w+)`", swap.group(1)) if swap else []
    if named != ORDER[:-1]:
        return replay_probe.fail(f"Swap up names {named}, not {ORDER[:-1]}")
    return replay_probe.Cases("tier order").finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

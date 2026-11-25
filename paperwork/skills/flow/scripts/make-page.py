#!/usr/bin/env python3
"""Build one standalone HTML page from a checked flow contract.

usage: make-page.py CONTRACT.json [PAGE.html]   check the contract, then write the page beside it as page.html, or at PAGE.html

The page holds its style, code and data inline and asks the network for nothing; the contract is its page data. A contract the checker
refuses builds no page: its breaks are printed and the exit status is 1."""
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from flow_order import before, critical, ranks  # noqa: E402
from page_parts import CARD, page  # noqa: E402
from tex_mathml import drawn  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
MARKUP = f"""<main id="diagram"><div id="stage"></div></main>
<nav id="crumbs" class="bar" aria-label="Levels"></nav>
<div id="tools" class="bar"><button id="search" class="tool quiet" type="button">Search <kbd>/</kbd></button></div>
{CARD}"""


def ordered(contract):
    """Each plan level's place of each task and milestone on the time axis, and its critical path, by level id."""
    found = {}
    for level in contract["levels"]:
        if level["kind"] == "plan":
            first = before(contract, level)
            tasks = {task["id"] for task in contract.get("tasks", []) if task["level"] == level["id"]}
            found[level["id"]] = {"ranks": ranks(first), "critical": critical(first, tasks)}
    return found


def main(args):
    if not 1 <= len(args) <= 2 or any(arg.startswith("-") for arg in args) or not pathlib.Path(args[0]).is_file():
        print(__doc__, file=sys.stderr)
        return 2
    source = pathlib.Path(args[0])
    checked = subprocess.run([sys.executable, str(HERE / "check-contract.py"), "check", str(source)], capture_output=True, text=True)
    if checked.returncode:
        print(checked.stdout + checked.stderr, end="", file=sys.stderr)
        return 1
    contract = json.loads(source.read_text())
    blocks = {"data": contract, "tags": json.loads((ASSETS / "tags.json").read_text()), "formulas": drawn(contract), "order": ordered(contract)}
    built = page(ASSETS, contract["title"], MARKUP, "Search nodes, edges, tasks and properties", blocks)
    target = pathlib.Path(args[1]) if len(args) == 2 else source.with_name("page.html")
    target.write_text(built)
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

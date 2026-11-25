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
from page_parts import CARD, code, palette, style  # noqa: E402
from tex_mathml import formulas, key, mathml  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
{parts_style}
{style}
</style>
</head>
<body>
<main id="diagram"><div id="stage"></div></main>
<nav id="crumbs" class="bar" aria-label="Levels"></nav>
<div id="tools" class="bar"><button id="search" class="tool quiet" type="button">Search <kbd>/</kbd></button></div>
{card}
{palette}
<script type="application/json" id="page-data">{data}</script>
<script type="application/json" id="page-threads">{{"threads": {{}}}}</script>
<script type="application/json" id="page-tags">{tags}</script>
<script type="application/json" id="page-formulas">{formulas}</script>
<script type="application/json" id="page-order">{order}</script>
<script>
{parts}
{code}
</script>
</body>
</html>
"""


def block(value):
    """JSON that is safe inside a script element."""
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def drawn(value):
    """The MathML of each formula a text of VALUE holds, by the name the page looks it up by."""
    if isinstance(value, dict):
        return {name: markup for part in value.values() for name, markup in drawn(part).items()}
    if isinstance(value, list):
        return {name: markup for part in value for name, markup in drawn(part).items()}
    found = {}
    for tex, display in formulas(value) if isinstance(value, str) else []:
        try:
            found[key(tex, display)] = mathml(tex, display)
        except ValueError:
            pass
    return found


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
    title = contract["title"].replace("&", "&amp;").replace("<", "&lt;")
    page = PAGE.format(title=title, parts_style=style(), style=(ASSETS / "page.css").read_text().strip(), card=CARD,
                       palette=palette("Search nodes, edges, tasks and properties"), parts=code(), code=(ASSETS / "page.js").read_text().strip(),
                       data=block(contract), tags=block(json.loads((ASSETS / "tags.json").read_text())), formulas=block(drawn(contract)), order=block(ordered(contract)))
    target = pathlib.Path(args[1]) if len(args) == 2 else source.with_name("page.html")
    target.write_text(page)
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

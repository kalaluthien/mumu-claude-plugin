#!/usr/bin/env python3
"""Build one standalone HTML page from a checked system contract.

usage: make-page.py CONTRACT.json [PAGE.html]   check the contract, then write the page beside it as page.html, or at PAGE.html

The page holds its style, code and data inline and asks the network for nothing; the contract is its page data. A contract the checker
refuses builds no page: its breaks are printed and the exit status is 1."""
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
{style}
</style>
</head>
<body>
<main id="diagram"><div id="stage" class="stage"></div></main>
<nav id="crumbs" class="bar" aria-label="Levels"></nav>
<div id="tools" class="bar">
<button id="scenarios" class="tool" type="button">Scenarios</button>
<button id="properties" class="tool" type="button">Properties</button>
<button id="search" class="tool quiet" type="button">Search <kbd>/</kbd></button>
</div>
<aside id="card" role="tooltip"></aside>
<div id="chip"></div>
<div id="play" class="bar">
<button id="prev" class="tool" type="button" aria-label="Previous step"><kbd>&larr;</kbd></button>
<span class="title"></span><span class="dots"></span>
<button id="next" class="tool" type="button" aria-label="Next step"><kbd>&rarr;</kbd></button>
<button id="stop" class="tool quiet" type="button" aria-label="Stop the scenario"><kbd>esc</kbd></button>
</div>
<div id="veil"></div>
<div id="palette" role="dialog" aria-label="Search">
<input id="query" type="text" placeholder="Search nodes, edges, scenarios and properties" autocomplete="off" spellcheck="false">
<div id="hits" role="listbox"></div>
<footer id="keys"><span><kbd>&uarr;</kbd><kbd>&darr;</kbd> move</span><span><kbd>&crarr;</kbd> open</span><span><kbd>esc</kbd> close</span></footer>
</div>
<script type="application/json" id="page-data">{data}</script>
<script type="application/json" id="page-threads">{{"threads": {{}}}}</script>
<script type="application/json" id="page-tags">{tags}</script>
<script>
{code}
</script>
</body>
</html>
"""


def block(value):
    """JSON that is safe inside a script element."""
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


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
    page = PAGE.format(title=title, style=(ASSETS / "page.css").read_text().strip(), code=(ASSETS / "page.js").read_text().strip(),
                       data=block(contract), tags=block(json.loads((ASSETS / "tags.json").read_text())))
    target = pathlib.Path(args[1]) if len(args) == 2 else source.with_name("page.html")
    target.write_text(page)
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

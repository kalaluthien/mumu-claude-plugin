#!/usr/bin/env python3
"""Build one standalone HTML page from a checked system contract.

usage: make-page.py CONTRACT.json [PAGE.html]   check the contract, then write the page beside it as page.html, or at PAGE.html

The page holds its style, code and data inline and asks the network for nothing; the contract is its page data. A contract the checker
refuses builds no page: its breaks are printed and the exit status is 1."""
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from contract_levels import nested  # noqa: E402
from page_parts import CARD, page  # noqa: E402
from tex_mathml import drawn  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
MARKUP = f"""<main id="diagram"><div id="stage" class="stage"></div></main>
<nav id="crumbs" class="bar" aria-label="Levels"></nav>
<div id="tools" class="bar">
<button id="scenarios" class="tool" type="button">Scenarios</button>
<button id="properties" class="tool" type="button">Properties</button>
<button id="search" class="tool quiet" type="button">Search <kbd>/</kbd></button>
</div>
{CARD}
<div id="chip"></div>
<div id="play" class="bar" role="toolbar" aria-label="Scenario">
<button id="prev" class="tool icon" type="button" aria-label="Previous step" title="Previous step (&larr;)"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg></button>
<button id="run" class="tool icon" type="button" aria-label="Play" title="Play or pause (space)"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path class="start" d="M7 4.5v15l12-7.5z" fill="currentColor"/><path class="pause" d="M8 5v14M16 5v14"/></svg></button>
<button id="next" class="tool icon" type="button" aria-label="Next step" title="Next step (&rarr;)"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg></button>
<span class="count"></span><span class="title"></span><span class="dots"></span><span id="onto" hidden></span>
<button id="again" class="tool" type="button" hidden>Replay</button>
<button id="onward" class="tool" type="button" hidden>Next scenario</button>
<button id="stop" class="tool icon quiet" type="button" aria-label="Close the scenario" title="Close (esc)"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18M6 6l12 12"/></svg></button>
</div>"""


def main(args):
    if not 1 <= len(args) <= 2 or any(arg.startswith("-") for arg in args) or not pathlib.Path(args[0]).is_file():
        print(__doc__, file=sys.stderr)
        return 2
    source = pathlib.Path(args[0])
    checked = subprocess.run([sys.executable, str(HERE / "check-contract.py"), "check", str(source)], capture_output=True, text=True)
    if checked.returncode:
        print(checked.stdout + checked.stderr, end="", file=sys.stderr)
        return 1
    contract = nested(json.loads(source.read_text()))
    blocks = {"data": contract, "tags": json.loads((ASSETS / "tags.json").read_text()), "formulas": drawn(contract)}
    built = page(ASSETS, contract["title"], MARKUP, "Search nodes, edges, scenarios and properties", blocks)
    target = pathlib.Path(args[1]) if len(args) == 2 else source.with_name("page.html")
    target.write_text(built)
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

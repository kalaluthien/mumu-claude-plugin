#!/usr/bin/env python3
"""Build one standalone HTML page from a checked system contract.

usage: make-page.py CONTRACT.json [PAGE.html]   check the contract, then write the page beside it as page.html, or at PAGE.html

The page holds its style, code and data inline and asks the network for nothing; the contract is its page data. CONTRACT.json may be a
folder of part files that `check-contract.py split` wrote. A contract the checker refuses builds no page: its breaks are printed and the
exit status is 1.

The page keeps each part's key, made of the part, what its check reads of the other parts and the code that checks and builds it; over
an earlier page, a part whose key is unchanged keeps its pieces from it, and only the other parts are checked and built again. It prints
the parts checked and built, the parts kept, then the page's path."""
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from contract_levels import nested  # noqa: E402
from contract_parts import SYSTEM, code_digest, keys, load, split  # noqa: E402
from contract_tags import catalogue  # noqa: E402
from page_parts import assembled, earlier, page, report  # noqa: E402
from tex_mathml import drawn, named  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
CODE = [HERE / "check-contract.py", HERE / "make-page.py", ASSETS / "tags.json", *(HERE.parents[2] / "lib").glob("*.py"), HERE.parents[2] / "lib" / "tags.json"]
MARKUP = """<main id="diagram"><div id="stage" class="stage"></div></main>
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


def breaks(source, names):
    """What the checker prints of the parts NAMES of SOURCE, or of all of it when NAMES is empty, when it finds a break, else ""."""
    done = subprocess.run([sys.executable, str(HERE / "check-contract.py"), "check", str(source), *[word for name in names for word in ("--part", name)]],
                          capture_output=True, text=True)
    return done.stdout + done.stderr if done.returncode else ""

def main(args):
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    if not 1 <= len(args) <= 2 or any(arg.startswith("-") for arg in args):
        print(__doc__, file=sys.stderr)
        return 2
    source = pathlib.Path(args[0])
    beside = source.absolute()  # a folder named by `..` is the one the OS opens; a link elsewhere stays as named
    target = pathlib.Path(args[1]) if len(args) == 2 else (beside.resolve() if beside.name == ".." else beside).with_name("page.html")
    try:
        contract = load(source, SYSTEM)
        parts = split(contract, SYSTEM)
    except (OSError, ValueError, RecursionError):
        print(breaks(source, []), end="", file=sys.stderr)
        return 1
    keyed = keys(parts, SYSTEM, code_digest(CODE))
    shown = earlier(target)
    changed = [name for name, key in keyed.items() if shown.get("parts", {}).get(name) != key]
    found = breaks(source, changed) if changed else ""
    if found:
        print(found, end="", file=sys.stderr)
        return 1
    drawn_before = shown.get("formulas") if isinstance(shown.get("formulas"), dict) else {}
    pieces, made = assembled(keyed, shown, lambda name: {"formulas": drawn(parts[name])},
                             lambda name: {"formulas": {key: drawn_before[key] for key in named(parts[name]) if key in drawn_before}})
    formulas = {key: markup for piece in pieces.values() for key, markup in piece["formulas"].items()}
    blocks = {"data": nested(contract), "tags": catalogue(ASSETS / "tags.json"), "formulas": formulas, "parts": keyed}
    target.write_text(page(ASSETS, contract["title"], MARKUP, blocks))
    print(report(keyed, made))
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

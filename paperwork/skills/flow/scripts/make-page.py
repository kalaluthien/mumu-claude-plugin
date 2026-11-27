#!/usr/bin/env python3
"""Build one standalone HTML page from a checked flow contract.

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
from flow_order import before, critical, ranks  # noqa: E402
from contract_parts import FLOW, TOP, code_digest, join, keys, load, split  # noqa: E402
from contract_tags import catalogue  # noqa: E402
from page_parts import assembled, earlier, page, report  # noqa: E402
from tex_mathml import drawn, named  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
CODE = [HERE / "check-contract.py", HERE / "make-page.py", ASSETS / "tags.json", *(HERE.parents[2] / "lib").glob("*.py"), HERE.parents[2] / "lib" / "tags.json"]
MARKUP = """<main id="diagram"><div id="stage"></div></main>"""


def ordered(contract):
    """Each plan level's place of each task and milestone on the time axis, and its critical path, by level id."""
    found = {}
    for level in contract["levels"]:
        if level["kind"] == "plan":
            first = before(contract, level)
            tasks = {task["id"] for task in contract.get("tasks", []) if task["level"] == level["id"]}
            found[level["id"]] = {"ranks": ranks(first), "critical": critical(first, tasks)}
    return found


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
        contract = load(source, FLOW)
        parts = split(contract, FLOW)
    except (OSError, ValueError, RecursionError):
        print(breaks(source, []), end="", file=sys.stderr)
        return 1
    keyed = keys(parts, FLOW, code_digest(CODE))
    shown = earlier(target)
    changed = [name for name, key in keyed.items() if shown.get("parts", {}).get(name) != key]
    found = breaks(source, changed) if changed else ""
    if found:
        print(found, end="", file=sys.stderr)
        return 1
    drawn_before = shown.get("formulas") if isinstance(shown.get("formulas"), dict) else {}
    order_before = shown.get("order") if isinstance(shown.get("order"), dict) else {}

    def make(name):
        alone = {TOP: {**parts[TOP], "levels": [parts[name]["id"]]}, name: parts[name]} if name != TOP else None
        return {"formulas": drawn(parts[name]), "order": ordered(join(alone, FLOW)) if alone else {}}

    def keep(name):
        held = {parts[name]["id"]: order_before[parts[name]["id"]]} if name != TOP and parts[name]["id"] in order_before else {}
        return {"formulas": {key: drawn_before[key] for key in named(parts[name]) if key in drawn_before}, "order": held}

    pieces, made = assembled(keyed, shown, make, keep)
    formulas = {key: markup for piece in pieces.values() for key, markup in piece["formulas"].items()}
    order = {level: entry for piece in pieces.values() for level, entry in piece["order"].items()}
    blocks = {"data": contract, "tags": catalogue(ASSETS / "tags.json"), "formulas": formulas, "order": order, "parts": keyed}
    target.write_text(page(ASSETS, contract["title"], MARKUP, blocks))
    print(report(keyed, made))
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

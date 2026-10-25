#!/usr/bin/env python3
"""Plan, build, lint, review and test an explanatory HTML book, and brief the agents that write it.

usage: make-book.py init DIR [--lang L]      copy the sample model and units into DIR
usage: make-book.py check [DIR]              plan rules (B) on book.json
usage: make-book.py build [DIR]              assemble book.html: chrome, references, facts, figures, review clones, math
usage: make-book.py lint [DIR] [--unit ID] [--quick]
usage: make-book.py mutate [DIR]             plant one defect per rule and pattern; fail if any is missed
usage: make-book.py stats FILE.html [--sel .CLASS|TAG]   per-unit size distribution, for bands and baselines
usage: make-book.py rules                    rule and policy tables
usage: make-book.py render [DIR] [--out DIR] [--quick]   book-wide #check plus element checks; prints failures only (needs playwright)
usage: make-book.py text [DIR] [--unit ID [--section N-M | --concept ID]] [--only prose|stems|cards|claims|figs]   flat reviewer text
usage: make-book.py snippet KIND | --list    markup snippet from assets/templates/units.html
usage: make-book.py outline [DIR] UNIT       one line per block: L<line> #<id> <kind> <meta> "<first 50>" <chars>
usage: make-book.py show [DIR] UNIT SEL [--html]   blocks by #id, data-c kind, L120 or L120-L180
usage: make-book.py edit [DIR] UNIT --patch F.json   all-or-none ops on the unit source; backup in .work/, rebuild, lint delta
usage: make-book.py shot [DIR] UNIT [--sel CSS] [--section N-M] [--solve] [--steps F.json] [--sheet] [--quick] [--out DIR]
usage: make-book.py demos [DIR] [--name N]   D['name'] demos in book.js: doc line, units, params; --name prints the source
usage: make-book.py pattern list [--family problem|visual] [--dir BOOK]
usage: make-book.py pattern show P
usage: make-book.py pattern promote P --dir BOOK [--as-variant-of Q]
usage: make-book.py element show E           an element's slots, checks and example
usage: make-book.py card new [DIR] --unit U --after SEL [--kind K] [--elements a,b] [--id ID] [--label P]   placeholder + slots/U.json stub (fig new: --kind fig|frames)
usage: make-book.py card lift [DIR] U ID     a hand card into slots/U.json, rendering back identical
usage: make-book.py brief [DIR] UNIT [--revise] [--as ID]           writer brief (<= 6k chars); --revise adds unit directives, lint todos, the kit
usage: make-book.py brief [DIR] --lens NAME --units U[:N],... [--as ID]   reviewer brief for one lens over units or unit sections
usage: make-book.py brief [DIR] [UNIT] --test WHAT | --debug SYMPTOM | --demo [NAME] | --research Q [--bulk] [--as ID]
usage: make-book.py brief [DIR] --fix RULES --units U[,U] [--render FILE] [--as ID]   fix brief (sources for E rules, fixer otherwise): the lint findings of those rules in those units
usage: make-book.py agents [DIR] STAGE [--units IDS] [--render FILE]   one line per task; STAGE = plan|write|review|test|demo|debug|fix (DIR before or after STAGE, or --dir);
    `--symptom S` belongs to debug only
    fix: lints, groups findings by unit; E rules -> `sources` (haiku; <= 12 notes or 3 units each), other unit rules -> `fixer` (sonnet; <= 25 findings, a part's
    units together), B* and G1 -> one `main` line for the lead. It also reads the reviewers' `.work/r-*/no.tsv` (unit TAB block id TAB row id TAB fix; rule `no:ROW`)
    and render findings (`--render FILE`, else `.work/render.json` or `.work/render.txt` if present; JSON rows or the printed `fail ...` lines; rule `render:CHECK`).
    The lead renames a processed no.tsv to no.done.tsv. Fix rounds go through this stage, with no hand-written briefs.
usage: make-book.py note [DIR] TEXT [--units IDS] [--topic T]        directive for the open round (opens the next one if the last is closed)
usage: make-book.py round [DIR] [show|close]                        list rounds or freeze the open one
usage: make-book.py approve [DIR] GATE --by user|self               record a gate approval with the current plan hash

Every command that takes DIR also takes --dir DIR (default .); a .work/ path in --patch, --out, --steps or --score resolves inside DIR.
Python standard library, plus node and KaTeX for math (fetched once into ~/.cache/paperwork-book). A book directory holds book.json (the model),
units.html or units/*.html (one <section data-u="ID"> per unit), optional figs/*.svg and facts.json, and receives book.html.
Figure scripts put paperwork/lib on sys.path, then `from book import glob, Fig, fact`.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from book import cli  # noqa: E402


def main(args):
    try:
        return cli.main(args) or 0
    except SystemExit as stop:
        if stop.code == 2:
            print(__doc__, file=sys.stderr)
        return stop.code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

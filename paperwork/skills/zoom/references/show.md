# Show

One checked Schema document drawn as one self-contained, read-only html page: a level at a time, overview first, with a node's detail on demand.

## Domain

- Page: the left navigation lists the document's levels; the body draws the shown level, with its `why`, its chart and a legend. It holds no way to answer, since a person reads it to understand a system.
- Chart: a part is a square box and a call a dashed arrow, a state a round box and a transition a solid arrow, an area a band around its nodes, and the initial state wears a dot.
- Detail: a click on a node or edge opens a panel with its description, source, rules and attributes; a click on a node that opens a level, by its link, draws that level.
- Worked pages: `../examples/<name>/page.html`, built from the `schema.json` beside them.

## Steps

1. Run `../scripts/make-page.py doc.json out.html`, which reads the document and refuses one that breaks the grammar or a scenario that leaves the edges. It runs no proof, so a page never waits on Alloy.
2. Run `uv run --with playwright==1.64.1 python3 ../scripts/make-page.py --check <dir>` over a folder of `<name>/schema.json`, until it prints `ok <n>` and a line per fact.
3. Run `--layout <dir>` the same way, until it prints `layout ok <n>`.
4. Run `--capture out.html <dir>` and look at each PNG; a measure cannot see a chart that reads badly.

## Rules

- **Long labels**: shorten a label a level cannot fit only after moving detail into `meta.description`, since the panel holds what a box cannot.
- **Kept pages**: build `../examples/<name>/page.html` again after a change to the page, since `--check` refuses a kept page that differs from the one built.

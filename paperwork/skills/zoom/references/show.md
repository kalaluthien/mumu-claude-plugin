# Show

One checked Schema document drawn as one self-contained, read-only html page: a level at a time, overview first, with a node's detail on demand and each scenario and proof played on the chart.

## Domain

- Page: the left navigation lists the document's levels, scenarios and rules; the body draws the shown level, with its `why`, its chart and a legend, and the root also lists what each other level holds. It holds no way to answer, since a person reads it to understand a system.
- Chart: a part is a square box and a call a dashed arrow, a state a round box and a transition a solid arrow, an area a band around its nodes, and the initial state wears a dot.
- Detail: a click on a node or edge opens a panel with its description, source, rules and attributes; a click on a node that opens a level, by its link, draws that level.
- Playback: picking a scenario or a rule opens its level, marks the path or the nodes it concerns, and shows a bar; Previous, Next and the numbered steps move along it, each with what it does and expects, and a rule's badge shows its verdict. A counterexample plays on the same bar and lists its whole run, and Back to start ends playback at the root. On a wide screen the bar sits beside the chart.
- Proofs file: what `prove-schema.py --proofs` writes, per rule its verdict, related nodes and a counterexample's steps. With none, the page lists its rules without a verdict.
- Worked pages: `../examples/<name>/page.html`, built from the `schema.json` and `proofs.json` beside them.

## Steps

1. Run `../scripts/make-page.py doc.json [proofs.json] out.html`, which reads the document and refuses one that breaks the grammar, names what a chart cannot place, or has a scenario that leaves the edges, and a proofs file that names a rule or node the document lacks. It runs no proof, so a page never waits on Alloy.
2. Run `uv run --with playwright==1.64.1 python3 ../scripts/make-page.py --check <dir>` over a folder of `<name>/schema.json`, until it prints `ok <n>` and a line per fact.
3. Run `--layout <dir>` the same way, until it prints `layout ok <n>`.
4. Run `--capture out.html <dir>` and look at each PNG; a measure cannot see a chart that reads badly.

## Rules

- **Long labels**: shorten a label a level cannot fit only after moving detail into `meta.description`, since the panel holds what a box cannot.
- **Kept pages**: build `../examples/<name>/page.html` again after a change to the page, and write `proofs.json` again after a change to the document, since `--check` refuses a kept page that differs from the one built.

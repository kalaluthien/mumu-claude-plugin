# HTML

One checked Schema document drawn by one view into one html page, read level by level: click a node to open the
level inside it, and play a scenario to watch it walk. The Schema says what is drawn; `view.json` says how, with the
reader's next action (`next`) under the page. Paths are relative to this file.

## Domain

- Engine: `html/assets/zoom.*`; view grammar: `html/assets/view-schema.json`; phone limits: `html/assets/phone-limits.json`.
- Drawing checks: `../../../../lib/page/view.py`; drawing measure: `../../../../lib/page/drawing.py`.
- Worked pairs: `../../examples/<name>/schema.json` and `view.json`.

## Steps

1. Unless the document has a `view.json` beside it, write one as [view-writing.md](html/view-writing.md) says, from `html/scripts/make-diagram.py new view.json`.
2. Run `uv run --with playwright==1.64.1 python3 html/scripts/make-diagram.py make doc.json view.json out.html`. It runs
   [check-schema.py](../schema/scripts/check-schema.py) on the document, then the drawing checks on the view, builds
   the page and checks the drawing in Chrome. Fix drawing problems in `view.json`, Schema problems in the document.
3. Review every level as a critic ([drawing-review.md](html/drawing-review.md)), then hand over.

A view written for the engine before the Schema carries over by `html/scripts/migrate-view.py old-view.json`.

## Layout

Each kind is drawn as its reading in [semantics.md](../schema/semantics.md) says, on a hand-drawn grid the view may
place by `x`, `y`:

- [Topology](../schema/semantics.md#topology): a component is a square box, a relation an arrow labelled with its field.
- [Workflow](../schema/semantics.md#workflow): an activity is a rounded box, a partition a band around its activities,
  a trigger a circle with an arrow in, and a port a stub into or out of the level.
- [State](../schema/semantics.md#state): a state is a round box, an event an arrow; the initial state takes a dot, one
  per region, and a sync is written on its events as `→ then` and `← when`.

A mark styles its node or arrow and joins the legend; a `diff` tints the node, or the arrow, green, red or amber. A
phone draws the top level in the columns that fit its width.

## Interaction

- A node that opens a level ([semantics.md](../schema/semantics.md#opening-a-level)) wears a chevron: a first click selects
  it, a second, or a click on the chevron, opens its level. The path above the drawing, or Escape, goes back up.
- Selecting a node or an arrow opens its note: what it is, its operations, rules, media and metadata. Metadata reads
  as [formats.md](formats.md) says, and with nothing selected the note shows the level's, and on the top level the
  document's.
- The level menu lists every level and the scenarios of the shown one.
- **Scenario animation**: a scenario from the menu plays its walk step by step: the step counter shows `<step> / <steps>`, `‹` and `›` or the
  arrow keys move one step, the rail jumps to any, and `✕` ends the run. Each step lights what it reaches, follows the
  walk into another level, and shows what the step does and expects. A rule that can break plays its breaking run the
  same way.

## Behaviours

Adopted from the whiteboard in https://news.hada.io/topic?id=34245 (#747); `html/scripts/probe-page.py behaviours`
checks each.

- viewer open-level: clicking a node that opens a level shows that level.
- viewer scenario-steps: a playing scenario shows a step counter and moves one step forward or back on `›` and `‹`.
- editor copy-for-agent: a selected node or arrow's note copies its level path, label and id for an agent to find it.

## Checks

- `html/scripts/make-diagram.py rules` lists the drawing checks and the plan's defaults; `html/scripts/prove-checks.py`
  shows each can fail.
- `html/scripts/probe-page.py labels|zoom|meta|behaviours page.html` checks a built page in Chrome; the pages in
  `html/fixtures/` each make one probe fail.

## Gotchas

- `make` never starts Alloy; it shows the answers last stored in `~/.cache/paperwork-alloy/results`.
- `fits` fails: give that level's nodes `x`, `y` in `view.json` ([view-writing.md](html/view-writing.md), Layout),
  not shorter labels.

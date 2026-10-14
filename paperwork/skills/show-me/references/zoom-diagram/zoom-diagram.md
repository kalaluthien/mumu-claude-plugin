# Zoom diagram

A **zoom diagram** is one checked system model drawn by one view into one html
page, read level by level, with the reader's next action (`next`) under it.
drill-it writes `system.json`; this playbook writes `view.json` and draws.
Paths are relative here.

## Setup

Optional: `../../../drill-it/scripts/check-system.py alloy --fetch` (needs
Java) downloads Alloy 6; `make` needs none.

## Interview

Before drill-it models, settle the plan as show-me's Asking says. Ask
intent, views, depth, prove (`rules` or `off`) and show, skipping what
is said. Depth picks which levels the views feature, not what the model holds.
`scripts/make-diagram.py rules` lists defaults.
[view-writing.md](view-writing.md) covers views, depth and show;
[model-writing.md](../../../drill-it/references/model-writing.md) (Plan) covers
intent and prove.

## Procedure

1. Interview.
2. Run `drill-it` with the plan's intent, prove and one purpose:
   `analyse-system` (exists), `design-system` (not built), `improve-system`
   with the original `system.json`. Draw each checked `system.json` returned.
3. Write `view.json` as [view-writing.md](view-writing.md) says, from
   `scripts/make-diagram.py new view.json`.
4. `uv run --with playwright python3 scripts/make-diagram.py make system.json
   view.json out.html` checks both files and builds the page. Fix a drawing
   problem in `view.json`; a system problem goes to drill-it.
5. Review every level as a critic ([drawing-review.md](drawing-review.md)),
   then hand over.

## Verification

Done when `make` ends in `ok`; it never starts Alloy and shows the last
answers drill-it's `--prove` stored. Tell the user:
- Each finding: a `must` rule the system can break, with its counterexample (a
  system defect, not a drawing one).
- What is unproved or only assumed ([proof-commands.md](../../../drill-it/references/proof-commands.md)).
- What Alloy did not cover ([proof-commands.md](../../../drill-it/references/proof-commands.md), Scopes).

Ask the user to try the Scenarios and say where a step reads wrong.

## Gotchas

- `check --prove` runs for minutes, or a command is unproved: [proof-commands.md](../../../drill-it/references/proof-commands.md) (top).
- `fits` fails: give that level's nodes `x` and `y` in `view.json` ([view-writing.md](view-writing.md), Layout), never shorter labels.
- Name refused as reserved (`steps`, `at`, `open`, `run`): drill-it renames it.

## Where things are

- View fields: `assets/view-schema.json`; system fields: `../../../drill-it/assets/system-schema.json`.
- Checks: `scripts/make-diagram.py rules`, `../../../../lib/diagram/view.py`, `../../../../lib/system/checks.py`.
- Engine: `assets/zoom-diagram.*`; phone limits: `assets/phone-limits.json`.
- Worked pairs: `examples/<name>/system.json` and `view.json`.

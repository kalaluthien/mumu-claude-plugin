# Zoom diagram

A **zoom diagram** is one checked system model drawn by one view into one html
page, read level by level, with the reader's next action (`next`) under it.
drill-it writes `system.json`; this playbook writes `view.json`, draws. Paths are relative.

## Setup

Optional: `../../../drill-it/scripts/check-system.py alloy --fetch` (needs
Java) downloads Alloy 6; `make` needs none.

## Interview

Before drill-it models, settle the plan as show-me's Asking says: ask
intent, views, depth, prove (`rules` or `off`) and show, skipping what
is said. Depth picks which levels the views feature, not the model.
`scripts/make-diagram.py rules` lists defaults. [view-writing.md](view-writing.md)
covers views, depth, show; [model-writing.md](../../../drill-it/references/model-writing.md)
(Plan) covers intent, prove.

## Procedure

1. Interview.
2. Run `drill-it` with the plan's intent, prove and one purpose:
   `analyse-system` (exists), `design-system` (not built), `improve-system`
   with the original `system.json`. Draw each checked `system.json`.
3. Write `view.json` as [view-writing.md](view-writing.md) says, from
   `scripts/make-diagram.py new view.json`.
4. `uv run --with playwright python3 scripts/make-diagram.py make system.json
   view.json out.html` checks both files, builds the page. Fix drawing
   problems in `view.json`; system problems go to drill-it.
5. Review every level as a critic ([drawing-review.md](drawing-review.md)), then hand over.

## Verification

Done when `make` ends in `ok`; it never starts Alloy; it shows the answers
drill-it's `--prove` last stored. Tell the user:
- Each finding: a `must` rule the system can break, with its counterexample
  (a system defect, not a drawing one).
- What is unproved, only assumed, or not covered by Alloy ([proof-commands.md](../../../drill-it/references/proof-commands.md), Scopes).

Ask the user to try the Scenarios and name any step that reads wrong.

## Gotchas

- `check --prove` runs minutes, or a command is unproved: [proof-commands.md](../../../drill-it/references/proof-commands.md) (top).
- `fits` fails: give that level's nodes `x`, `y` in `view.json` ([view-writing.md](view-writing.md), Layout), not shorter labels.
- Name refused as reserved (`steps`, `at`, `open`, `run`): drill-it renames.

## Where things are

- Schemas: view `assets/view-schema.json`, system `../../../drill-it/assets/system-schema.json`.
- Checks: `scripts/make-diagram.py rules`, `../../../../lib/diagram/view.py`, `../../../../lib/system/checks.py`.
- Engine: `assets/zoom-diagram.*`; phone limits: `assets/phone-limits.json`.
- Worked pairs: `examples/<name>/system.json`, `view.json`.

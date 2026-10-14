# Zoom diagram

A **zoom diagram** is one checked system model drawn by one view into one html
page, read level by level, with the reader's next action (`next`) under it.
drill-it writes `system.json`; this playbook writes `view.json`, draws. Paths are relative.

## Interview

Before drill-it models, settle the plan as show-me's Asking says: ask
intent, views, depth, prove (`rules` or `off`) and show, skipping what
is said. Depth picks which levels the views feature, not the model.
`scripts/make-diagram.py rules` lists defaults. [view-writing.md](view-writing.md)
covers views, depth, show; `drill-it` covers intent, prove.

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
- What is unproved, only assumed, or not covered by Alloy: `drill-it`'s hand-back lists them.

Ask the user to try the Scenarios and name any step that reads wrong.

## Gotchas

- A proof runs minutes, or a command is unproved: send it back to `drill-it`.
- `fits` fails: give that level's nodes `x`, `y` in `view.json` ([view-writing.md](view-writing.md), Layout), not shorter labels.
- Name refused as reserved (`steps`, `at`, `open`, `run`): drill-it renames.

## Where things are

- Schemas: view `assets/view-schema.json`, system: the model follows `drill-it`'s schema, and `scripts/make-diagram.py check` validates it.
- Checks: `scripts/make-diagram.py rules`, `../../../../lib/diagram/view.py`, `../../../../lib/system/checks.py`.
- Engine: `assets/zoom-diagram.*`; phone limits: `assets/phone-limits.json`.
- Worked pairs: `examples/<name>/system.json`, `view.json`.

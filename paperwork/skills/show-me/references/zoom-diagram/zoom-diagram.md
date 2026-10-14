# Zoom diagram

Paths here are relative to this file.

A **zoom diagram** is one checked system model drawn by one view into one html
page, read level by level, with the reader's next action (`next`) under it.
drill-it writes the system model (`system.json`); this playbook writes the view
(`view.json`) and draws.

## Setup

Optional, once per machine: `../../../drill-it/scripts/check-system.py alloy --fetch`
downloads Alloy 6 (needs Java). `make` needs no Alloy.

## Interview

Before drill-it models, settle the plan with the user as show-me's Asking
says.

Ask for the plan's intent, views, depth, prove (`rules` or `off`) and show, skipping only what
the user has already said; depth is a choice of which levels the views feature,
never of what the model holds; `scripts/make-diagram.py rules` lists each with its
default. [view-writing.md](view-writing.md) explains views, depth and show;
[model-writing.md](../../../drill-it/references/model-writing.md) (Plan) explains
intent and prove.

## Procedure

1. Interview.
2. Run `drill-it` with the plan's intent and prove and one purpose:
   `analyse-system` for a system that exists, `design-system` for one not yet
   built, `improve-system` with the original `system.json` to improve one. It
   hands back each checked `system.json` and its findings; draw each.
3. Write `view.json` as [view-writing.md](view-writing.md) says, from
   `scripts/make-diagram.py new view.json`.
4. `uv run --with playwright python3 scripts/make-diagram.py make system.json
   view.json out.html` checks both files and builds the page. A drawing problem
   is fixed in `view.json`; a problem of the system goes back to drill-it.
5. Look at every level as a critic ([drawing-review.md](drawing-review.md)),
   then hand over.

## Verification

A diagram is done when `make` ends in `ok`; `make` never starts Alloy and shows
the last answers drill-it's `--prove` stored. Tell the user, in the hand-over,
what that does and does not cover:
- Name each finding: a `must` rule the system can break, with its
  counterexample, as a defect of the system and not of the drawing.
- Name what is unproved, and which rules are only assumed
  ([proof-commands.md](../../../drill-it/references/proof-commands.md) says what each standing means).
- Say what Alloy did not cover ([proof-commands.md](../../../drill-it/references/proof-commands.md), Scopes).
Ask the user to try the Scenarios on the page and say where a step reads
wrong.

## Gotchas

| Symptom | Fix |
|---|---|
| `check --prove` runs for minutes, or a command is unproved | [proof-commands.md](../../../drill-it/references/proof-commands.md) (top) |
| `fits` fails | give that level's nodes `x` and `y` in `view.json` ([view-writing.md](view-writing.md), Layout), never shorter labels |
| a name is refused as reserved | Alloy and the translation reserve words such as `steps`, `at`, `open`, `run`; drill-it renames the model's word |

## Where things are

| For | Read or run |
|---|---|
| every field of the view file | `assets/view-schema.json` |
| every field of the system file | `../../../drill-it/assets/system-schema.json` |
| each check and parameter | `scripts/make-diagram.py rules`, `../../../../lib/diagram/view.py`, `../../../../lib/system/checks.py` |
| the drawing engine | `assets/zoom-diagram.js`, `.css`, `.html` |
| a phone's limits, shared by the engine and the checks | `assets/phone-limits.json` |
| worked pairs | `examples/<name>/system.json` and `view.json` |

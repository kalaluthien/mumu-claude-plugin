# Zoom diagram

Paths here are relative to this file.

A **zoom diagram** is one checked system model drawn by one view, read level
by level, as a part show-me places on its page or as a page of its own with the
reader's next action (`next`) under it.
drill-it writes the system model (`system.json`); this playbook writes the view
(`view.json`) and draws.

## Setup

Once per machine: `../../../drill-it/scripts/check-system.py alloy --fetch`
downloads Alloy 6 (needs Java).

## Interview

Before drill-it models, settle the plan with the user as show-me's Asking
says.

Ask for the plan's intent, views, depth, prove and show, skipping only what
the user has already said; `scripts/make-diagram.py rules` lists each with its
default. [view-writing.md](view-writing.md) explains views, depth and show;
[model-writing.md](../../../drill-it/references/model-writing.md) (Plan) explains
intent and prove.

## Procedure

1. Interview.
2. Run `drill-it` with the plan's intent and prove and the purpose `zoom-diagram`;
   it hands back a checked `system.json` and its findings.
3. Write `view.json` as [view-writing.md](view-writing.md) says, from
   `scripts/make-diagram.py new view.json`.
4. `uv run --with playwright python3 scripts/make-diagram.py make system.json
   view.json out.html` checks both files and builds the page. A drawing problem
   is fixed in `view.json`; a problem of the system goes back to drill-it.
5. Placed on a show-me page: `scripts/make-diagram.py part system.json
   view.json part.html` writes the part's body.
6. Look at every level as a critic ([drawing-review.md](drawing-review.md)),
   then hand over.

## Parts

The engine draws each from the two files; `show` turns off an optional one.

| part | use | holds |
| --- | --- | --- |
| Levels | required | the root and each level a node opens, nodes placed by `view.json` |
| Next | required | `next`, under a page of its own; a placed part leaves it to the page's Next |
| Notes | optional | per node, its facts and the design decision inside it |
| Scenarios | optional | each Scenario replayed step by step (`replay`) |
| Rules | optional | each rule's formula and its standing from Alloy (`formulas`) |
| Screens | optional | mock screens with the node's block picked out (`media`) |

## Verification

A diagram is done when `make` ends in `ok`. Tell the user, in the hand-over,
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
| a full check runs for minutes, or a command is unproved | [proof-commands.md](../../../drill-it/references/proof-commands.md) (top) |
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

# Zoom diagram

Paths here are relative to this file.

A **zoom diagram** is one checked `model.json` built into one html page, read
level by level, with the model's `next` under it.

## Setup

Once per machine: `scripts/make-diagram.py alloy --fetch` downloads Alloy 6
(needs Java).

## Interview

Before drill-it models, settle the plan with the user as show-me's Asking
says.

| Question | Becomes |
|---|---|
| the question they want answered | `plan.intent` |
| the diagrams they expect | `plan.views` |
| what to open deeply, what to leave closed | `deep`, `shallow`, `depth` ([model-writing.md](model-writing.md), Depth) |
| what Alloy should prove, and anything not to show | `prove`, `show` |

Skip only what the user has already said. [model-writing.md](model-writing.md)
(Plan) has typical plans per intent.

## Steps

1. Interview.
2. Run `drill-it` with the plan and the form `zoom diagram`; it hands back a checked
   `model.json`.
3. `uv run --with playwright python3 scripts/make-diagram.py make model.json
   out.html` checks, builds and checks the
   zoom diagram.
4. Look at every level as a critic ([drawing-review.md](drawing-review.md)),
   then hand over.

## Verification

A model is done when `make` ends in `ok`. Tell the user, in the hand-over,
what that does and does not cover:
- Name what is unproved or can break, and which rules are only assumed
  ([proof-commands.md](proof-commands.md) says what each standing means).
- Say what Alloy did not cover ([proof-commands.md](proof-commands.md), Scopes).
Ask the user to try the Scenarios on the page and say where a step reads
wrong.

## Gotchas

| Symptom | Fix |
|---|---|
| a full check runs for minutes, or a command is unproved | [proof-commands.md](proof-commands.md) (top) |
| `fits` fails | give that level's nodes `x` and `y` ([model-writing.md](model-writing.md), Layout), never shorter labels |
| a name is refused as reserved | Alloy and the translation reserve words such as `steps`, `at`, `open`, `run`; rename the model's word |

## How to fix

When the playbook itself is wrong (a check refuses something legitimate, a
reference misses a case, the engine draws badly):
- change the one file that owns it (a reference Steps links, or a row below),
  never a single model to get around it;
- run `scripts/prove-checks.py` (`--prove` adds Alloy), which names a check
  with no mutation that makes it fail, and `make` every example.

## Where things are

| For | Read or run |
|---|---|
| every field of the model file | `assets/model-schema.json` |
| each check and parameter | `scripts/make-diagram.py rules`, `../../../../lib/diagram/checks.py`, `../../../../lib/diagram/plan.py` |
| the drawing engine | `assets/zoom-diagram.js`, `.css`, `.html` |
| a phone's limits, shared by the engine and the checks | `assets/phone-limits.json` |
| worked models | `examples/*.json` |

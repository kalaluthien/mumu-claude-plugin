# Zoom diagram

A whole system to analyse, design or learn (software, a process, a protocol,
an organization, a body of knowledge) as one checked diagram the reader zooms
through. Paths here are relative to this file.

## Output

One model file (`model.json`) of the system's Scenarios, Operations, Rules
and nested levels, checked by the scripts and by Alloy 6, and built into one
html **zoom diagram**: a hand-drawn diagram read level by level, with a note
beside whatever is selected, and under it the model's `next`: the reader's next
action or choice, in one sentence.

## Setup

Once per machine: `scripts/make-diagram.py alloy --fetch` downloads Alloy 6
(needs Java).

## Interview

Before modelling, settle the plan with the user in one `AskUserQuestion`
batch, `grill-me` style: propose a concrete answer for each and let them
correct it.

| Ask | Becomes |
|---|---|
| the question they want answered | `plan.intent` |
| the diagrams a practitioner of this domain expects | `plan.views`, each drawn by a level or left out with why |
| what to open deeply, what to leave closed | `deep`, `shallow`, `depth` ([model-writing.md](model-writing.md), Depth) |
| what Alloy should prove | `prove` |
| anything not to show | `show` |

Skip only what the user has already said. [model-writing.md](model-writing.md)
(Plan) has typical plans per intent.

## Flow

1. Read the system: code, docs, configs, screens. `scripts/make-diagram.py
   new model.json` starts a valid file.
2. Interview.
3. Model in the order of [model-writing.md](model-writing.md): Scenarios and
   their walks, levels, quantities, operations, rules, names, then text,
   media and `next`.
4. `scripts/make-diagram.py check model.json --quick` after each edit; the
   full check (with Alloy) once the quick one passes.
5. `uv run --with playwright python3 scripts/make-diagram.py make model.json
   out.html` (it drives the installed Chrome) checks, builds and checks the
   zoom diagram at 390 and 1200 px, light and dark.
6. Look at every level as a critic ([drawing-review.md](drawing-review.md)),
   then hand over.

## Verification

A model is done when `make` ends in `ok`. Tell the user, in the hand-over,
what that does and does not cover:
- Name what is unproved or can break, and which rules are only assumed
  ([proof-commands.md](proof-commands.md) says what each standing means).
- Say what Alloy did not cover ([proof-commands.md](proof-commands.md), Scopes).
Ask the user to try the Scenarios on the page and say where a step reads
wrong; that is the check no script makes.

## Gotchas

| Symptom | Fix |
|---|---|
| a full check runs for minutes, or a command is unproved | [proof-commands.md](proof-commands.md) (top) |

## How to fix

When the playbook itself is wrong (a check refuses something legitimate, a
reference misses a case, the engine draws badly):
- change the one file that owns it (a reference Flow links, or a row below),
  never a single model to get around it;
- run `scripts/prove-checks.py` (`--prove` adds Alloy), which names a check
  with no mutation that makes it fail, and `make` every example.

## Where things are

| For | Read or run |
|---|---|
| every field of the model file | `assets/model-schema.json` |
| each check and parameter | `scripts/make-diagram.py rules`, `../../../../lib/diagram/checks.py`, `../../../../lib/diagram/plan.py` |
| the drawing engine | `assets/zoom-diagram.js`, `.css`, `.html` |
| worked models | `examples/*.json` |

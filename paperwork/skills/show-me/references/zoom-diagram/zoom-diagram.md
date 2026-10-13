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
(needs Java), and every command that draws runs under
`uv run --with playwright python3`, which drives the installed Chrome.

## Interview

Before modelling, settle the plan with the user in one `AskUserQuestion`
batch, `grill-me` style: propose a concrete answer for each and let them
correct it.

| Ask | Becomes |
|---|---|
| the question they want answered | `plan.intent` |
| the diagrams a practitioner of this domain expects | `plan.views`, each drawn by a level or left out with why |
| what to open deeply, what to leave closed | `deep`, `shallow`, `depth` |
| what Alloy should prove | `prove` |
| anything not to show | `show` |

Skip only what the user has already said. [model-writing.md](model-writing.md)
(Plan) has typical plans per intent.

## Flow

1. Read the system: code, docs, configs, screens. `scripts/make-diagram.py
   new model.json` starts a valid file.
2. Interview (above).
3. Model in the order of [model-writing.md](model-writing.md): Scenarios and
   their walks, levels, quantities, operations, rules, names, then text,
   media and `next`.
4. `scripts/make-diagram.py check model.json --quick` after each edit; the
   full check (with Alloy) once the quick one passes.
5. `uv run --with playwright python3 scripts/make-diagram.py make model.json
   out.html` checks, builds and checks the drawing at 390 and 1200 px, light
   and dark.
6. Look at every level as a critic ([drawing-review.md](drawing-review.md)),
   then hand over.

## Verification

A model is done when `check` ends in `ok` and `render` in `ok`. Tell the user,
in the hand-over, what that does and does not cover:
- `ok (unproved: …)` names Alloy commands that did not finish or did not run;
  say which rules or Scenarios they are.
- `note … can break` lists should-rules Alloy broke, with the run; `assumed`
  lists must-rules Alloy only assumed.
- Alloy checks within small bounds, not for every size, and reads no
  quantities and no links between zoom levels.
Ask the user to try the Scenarios on the page and say where a step reads
wrong; that is the check no script makes.

## Gotchas

| Symptom | Fix |
|---|---|
| a full check runs for minutes | edit with `--quick`; each Alloy command stops after 120 s (`ZOOM_DIAGRAM_ALLOY_SECONDS`) and reports as unproved; answers are cached, so only changed commands rerun |
| an unproved command on every run | shrink the rule's scope or split the rule; raise `ZOOM_DIAGRAM_ALLOY_SECONDS` only to confirm once |
| `fits` fails | give that level's nodes `x` and `y`, never shorter labels |
| the root level is cut off in the 390 px capture | the root is the first screen: give its nodes `x` and `y` so it fits a phone's width without scrolling |
| a name is refused as reserved | Alloy and the translation reserve words such as `steps`, `at`, `open`, `run`; rename the model's word |
| a check seems wrong for this system | fix the model if the check is right about it; otherwise see How to fix |
| a mock screen looks generic | rebuild it from the code that draws the screen ([model-writing.md](model-writing.md), Screens) |

## How to fix

When the playbook itself is wrong (a check refuses something legitimate, a
reference misses a case, the engine draws badly):
- change the one file that owns it (table below), never a single model to
  get around it;
- a changed or new check gets a mutation in `scripts/prove-checks.py` that
  makes it fail;
- run `scripts/prove-checks.py` (`--prove` adds Alloy) and `make` every
  example; keep `examples/self.json`, the model of this playbook, true to the
  change.

## Where things are

| For | Read or run |
|---|---|
| plan, Scenarios, levels, quantities, operations, rules, names, layout, sentences, screens, media | [model-writing.md](model-writing.md) |
| the Alloy module, its commands, what an Alloy problem means | [proof-commands.md](proof-commands.md) |
| how the zoom diagram looks and behaves; the critic's pass | [drawing-review.md](drawing-review.md) |
| every field of the model file | `assets/model-schema.json` |
| each check and parameter | `scripts/make-diagram.py rules`, `../../../../lib/diagram/checks.py`, `../../../../lib/diagram/plan.py` |
| the drawing engine | `assets/zoom-diagram.js`, `.css`, `.html` |
| worked models | `examples/*.json`: a pull request, a company, a skill, a viewer, a trial, a proof; `self.json` models this playbook |

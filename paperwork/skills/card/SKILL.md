---
name: card
description: Use when a target, such as a document, skill, code, page or plan, must be graded into an HTML report card, or when writing, measuring, applying or repairing a grading rubric for a judge, a benchmark or a human grading sheet. Not for a quick A-against-B check of a change.
---

# card

Grade a target into a report card: find what it is and who it serves, derive a rubric of binary criteria for it, grade it with quoted evidence, and show the result as one HTML page. The rubric is one JSON file in the grammar of [references/spec/assets/rubric-schema.json](references/spec/assets/rubric-schema.json), with criteria in tiers that never trade off; `spec` names the file that holds a rubric (`spec.json`, `check-spec.py`, `score-spec.py`); [references/spec/model.md](references/spec/model.md) says what it means, [references/spec/criteria.md](references/spec/criteria.md) how to write a criterion, and [references/spec/changelog.md](references/spec/changelog.md) what each grammar version added.

## Domain

- **criterion**: one observable proposition about an answer, met or not; a `-` criterion names an error.
- **tier**: criteria that may trade off; a higher tier always outranks every lower one together.
- **exchange record**: the recorded answer to "which answer would the expert ship", which places two criteria in tiers.
- **judge error** and **delta**: per tier, the chance the judge flips a verdict and the smallest difference no lower tier may overturn; the weights come from them.
- **verdict file**: each answer's 0 or 1 per criterion, its groups and who it beats.
- **grades file**: one target's verdicts with their evidence, reasons and fixes, from which the report card is built.

## Route

`Read` the playbook of the first row that fits the ask.

| ask | playbook |
| --- | --- |
| grade a target and show the result, or raise a target by its grade | [references/report.md](references/report.md) |
| write a rubric from a task | [references/author.md](references/author.md) |
| how far the judge, or a model counting items in prose, agrees with itself or with people, or how it reacts to length, padding or wording | [references/calibrate.md](references/calibrate.md) |
| apply a rubric to verdicts: rewards for training, a comparison of systems, a sheet people fill in | [references/grade.md](references/grade.md) |
| a rubric ranked answers wrongly | [references/repair.md](references/repair.md) |

## Rules

- **Checked rubric**: run `${CLAUDE_PLUGIN_ROOT}/skills/card/references/spec/scripts/check-spec.py check <spec>` after every edit; a rubric that does not print `ok` grades nothing.
- **Scripts compute**: weights, scores, orders and agreement come from `check-spec.py`, `${CLAUDE_PLUGIN_ROOT}/skills/card/scripts/score-spec.py` and `${CLAUDE_PLUGIN_ROOT}/skills/card/scripts/measure-judge.py`, never from your own arithmetic; report cards come from `${CLAUDE_PLUGIN_ROOT}/skills/card/scripts/make-report.py`.
- **One page**: every report uses the same page; change the rubric or the grades, never the page.
- **Check the page**: `uv run --with playwright==1.64.1 python3 ${CLAUDE_PLUGIN_ROOT}/skills/card/scripts/make-report.py --check ${CLAUDE_PLUGIN_ROOT}/skills/card/examples` builds each example and checks its scores, cards and fix list in headless Chromium; `--layout` checks 390 and 1200 px, light and dark; `--capture <page.html> <dir>` writes PNGs to look at.
- **Samples**: [examples/](examples/) holds finished rubrics migrated from real ones, and one folder per graded target with its `spec.json`, `grades.json` and the `report.html` they build; `card-skill/` is this skill graded by itself, with each round in `rounds.json`.

---
name: quiz
description: Use when turning a task into a grading spec for a judge reward, a benchmark or a human grading sheet, or when measuring, applying or repairing one. Not for a quick A-against-B check of a change.
---

# quiz

Turn a task into a grading spec: binary criteria in tiers that never trade off, with weights derived from how often the judge errs, then measure the judge, grade by the spec and repair it. The spec is one JSON file in the grammar of [references/spec/assets/rubric.schema.json](references/spec/assets/rubric.schema.json); [references/spec/model.md](references/spec/model.md) says what it means and [references/spec/criteria.md](references/spec/criteria.md) how to write a criterion.

## Domain

- **criterion**: one observable proposition about an answer, met or not; a `-` criterion names an error.
- **tier**: criteria that may trade off; a higher tier always outranks every lower one together.
- **exchange record**: the recorded answer to "which answer would the expert ship", which places two criteria in tiers.
- **judge error** and **delta**: per tier, the chance the judge flips a verdict and the smallest difference no lower tier may overturn; the weights come from them.
- **verdict file**: each answer's 0 or 1 per criterion, its groups and who it beats.

## Route

`Read` the playbook of the first row that fits the ask.

| ask | playbook |
| --- | --- |
| write a rubric, reward spec or grading spec from a task | [references/playbook/author.md](references/playbook/author.md) |
| how far the judge agrees with itself or with people, or how it reacts to length, padding or wording | [references/playbook/calibrate.md](references/playbook/calibrate.md) |
| apply a spec to verdicts: rewards for training, a comparison of systems, a sheet people fill in | [references/playbook/grade.md](references/playbook/grade.md) |
| a spec ranked answers wrongly | [references/playbook/repair.md](references/playbook/repair.md) |

## Rules

- **Checked spec**: run `${CLAUDE_PLUGIN_ROOT}/skills/quiz/references/spec/scripts/check-spec.py check <spec>` after every edit; a spec that does not print `ok` grades nothing.
- **Scripts compute**: weights, scores, orders and agreement come from `check-spec.py`, `${CLAUDE_PLUGIN_ROOT}/skills/quiz/scripts/score-spec.py` and `${CLAUDE_PLUGIN_ROOT}/skills/quiz/references/playbook/scripts/measure-judge.py`, never from your own arithmetic.
- **Samples**: [examples/](examples/) holds finished specs migrated from real rubrics.

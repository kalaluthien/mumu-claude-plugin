# Author

Turn a task into a spec that checks, in the grammar of [spec/assets/rubric.schema.json](spec/assets/rubric.schema.json). Write criteria as [spec/criteria.md](spec/criteria.md) says; [spec/model.md](spec/model.md) says what the tiers and weights mean.

## Interview

Before Frame, ask one `AskUserQuestion` batch: the deliverable and its reader, the worst plausible failure, which differences the person would ignore (this sets each delta), the judge model and the label budget, and the use (train, eval or human). After Tiers, ask one batch for the exchange pairs you hesitate on and the mask questions. Never ask what a draft criterion or a boundary test settles.

## Steps

| step | writes | gate |
| --- | --- | --- |
| 1 Frame | the task's world (as of, scope, deliverable), its evidence goal and use | two experts would agree what a complete answer covers; no hidden assumption of one person, such as "top 10" by what |
| 2 Answer space | three or more valid answers that differ in order and wording, three or more near-misses, a list of failures | each failure an expert names maps to a candidate criterion |
| 3 Criteria | each criterion with its polarity, check, provenance, passing variants and near-misses | the boundary test: every variant passes, every near-miss fails |
| 4 Tiers | tiers and exchange records, by the exchange test | `check-spec.py check` prints `ok`; pairs you hesitate on settled by the person and recorded as theirs |
| 5 Error and thresholds | each tier's judge error and delta; a mask and its pass rate where it applies | `check-spec.py weights` printed; every warning fixed or answered in a note |
| 6 Process | the judge, group size and monitor signals | a calibration plan stated: [calibrate.md](calibrate.md) |

- **Frame first**: fix the world in the task statement before any criterion; a criterion copied from one person's request inherits their unstated preference and fails other correct answers.
- **Judge error estimate**: take it from human labels on 30 or more answers when they exist. Otherwise estimate it (program about 0.01 to 0.03, a concrete judge criterion about 0.05, a judgement-heavy one 0.1 to 0.2) and mark the calibration estimated.
- **Concrete top**: a high judge error on a top tier makes every lower weight tiny; rewrite its criteria to be concrete or program-checked rather than move the tier down.
- **Mask question**: at each tier boundary ask "among answers that fail this tier, is a better lower-tier score still better?"; no means a mask, with a pass rate estimate.
- **Few tiers**: prefer two to four criterion tiers, since each extra tier shrinks the lower weights geometrically.

**Reward-hacking probe**: the probe is one answer built to pass the criteria while failing the intent, such as the right keywords with no substance, padding, or a format with nothing in it. Write it, grade it and a genuine answer as the judge would into one verdict file, and run `${CLAUDE_PLUGIN_ROOT}/skills/quiz/scripts/score-spec.py order <spec> <verdicts>`. The probe must rank below the genuine answer; when it does not, the criterion it fooled is missing or too vague: go back to step 2 or 3.

**Dry run**: done when `check-spec.py check` prints `ok`, the probe ranks below, and a dry run agrees with the person. Grade one strong, one middling and two near-miss answers. Run `score-spec.py order`, and compare with the person's own order of the same four. Show them the tier table, the printed weights and that order; a disagreement goes back to step 4.

## Gotchas

- **Tiers, not weights**: a weighted sum with a large negative item still lets the other items compensate unless that item outweighs them all; that is what tiers are for.
- **Flat rubric**: a hierarchy of weighted averages is a flat rubric; structure matters only through tiers and masks.

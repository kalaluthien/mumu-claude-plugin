# Calibrate the judge

Measure how far a judge's verdicts on a spec can be trusted, and set each tier's judge error from what you measure. The spec is in the grammar of [../spec/assets/rubric.schema.json](../spec/assets/rubric.schema.json); [../spec/model.md](../spec/model.md) says why agreement bounds the weights.

The commands are `${CLAUDE_PLUGIN_ROOT}/skills/litmus/references/playbook/scripts/measure-judge.py <mode> <spec> …`; each prints what its numbers mean.

## Steps

1. **Full rubric**: the judge grades every criterion of the spec in one call, with the whole rubric in view.
2. **Runs**: grade the same 30 or more answers three times into one folder of verdict files and run `alpha <spec> <folder>`. Rewrite each criterion it names below 0.800; never reweight it.
3. **People**: with human verdicts on the same answers, run `human <spec> <judge verdicts> <human verdicts>`. Record kappa, macro F1 and the MET-rate gap in the spec's judge calibration. A judge that says met more often than people is lenient, and lenience is what optimisation exploits.
4. **Perturbations**: for each answer `a`, add answers named `a~<kind>` that change only one surface, and run `bias <spec> <verdicts>`:
   - paraphrase: the same content in other words;
   - padding: the same content with filler added;
   - length: the same content shorter or longer;
   - order-swap: the same parts in another order;
   - mentioned-not-committed: the answer names an error to warn against it, without committing it.
   A kind flagged above a tier's judge error is a bias of that tier; rewrite the criteria it moves, or raise the tier's judge error to what you measured and rerun `check-spec.py weights`.
5. **Judge error**: set each tier's judge error from the flips you measured, and mark the calibration no longer estimated.

## Monitor

During training, watch the signals the spec's monitor lists, and at least these:
- reward rising while held-out expert pairwise wins stay flat: the policy found a gap in the criteria;
- the MET rate of one criterion drifting: the policy learned to satisfy the judge's reading of it;
- answer length trending up: a length bias the perturbation suite missed.

Each one sends the spec to [repair.md](repair.md).

## Gotchas

- **Biases add up**: judge biases within one tier, such as length or wording, add up, and the tier condition does not remove them; the perturbation suite measures them.
- **Hidden mask**: top-down routing, where the judge picks a branch and then grades its children, is a hidden mask with compounding judge error; grade every criterion with the full rubric instead.

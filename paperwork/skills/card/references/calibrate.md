# Calibrate

Measure how far a judge's verdicts on a spec can be trusted, and set each tier's judge error from what you measure.

The commands are `${CLAUDE_PLUGIN_ROOT}/skills/card/scripts/measure-judge.py <mode> <spec> …`; each prints what its numbers mean. [spec/model.md](spec/model.md) says why agreement bounds the weights.

## Steps

1. **Full rubric**: the judge grades every criterion of the spec in one call, with the whole rubric in view.
2. **Runs**: grade the same 30 or more answers three times into one fresh folder of verdict files (never one an older run still writes: its stale replies become cache) and run `alpha <spec> <folder>`. Rewrite each criterion it names below 0.800; never reweight it. Keep a criterion only while the sample leaves it headroom: one every answer meets, or whose anchors all sit at the top, measures nothing. A completeness score counts against a fixed key built from the sources, never gaps raised from the model's own text, and the key's size sets its ceiling.
3. **People**: with human verdicts on the same answers, run `human <spec> <judge verdicts> <human verdicts>`. Record kappa, macro F1 and the MET-rate gap in the spec's judge calibration. A judge that says met more often than people is lenient, and lenience is what optimisation exploits.
4. **Perturbations**: for each answer `a`, add answers named `a~<kind>` that change only one surface, and run `bias <spec> <verdicts>`:
   - paraphrase: the same content in other words;
   - padding: the same content with filler added;
   - length: the same content shorter or longer;
   - order-swap: the same parts in another order;
   - mentioned-not-committed: the answer names an error to warn against it, without committing it.
   A kind flagged above a tier's judge error is a bias of that tier; rewrite the criteria it moves, or raise the tier's judge error to what you measured and rerun `check-spec.py weights`.
5. **Judge error**: set each tier's judge error from the flips you measured, and mark the calibration no longer estimated.

**Monitor**

During training, watch the signals the spec's monitor lists, and at least these:
- reward rising while held-out expert pairwise wins stay flat: the policy found a gap in the criteria;
- the MET rate of one criterion drifting: the policy learned to satisfy the judge's reading of it;
- answer length trending up: a length bias the perturbation suite missed.

Each one sends the spec to [repair.md](repair.md).

## Rules

- **Noise and bias**: judge biases within one tier, such as length or wording, add up, and the tier condition does not remove them; the perturbation suite measures them. A model's count or score also moves run to run: let code cut the text into numbered sentences and pick each one's nearest pairs by word Jaccard, let the model score single items 0 or 1, ask 3 times and keep the median or 2 of 3, in parts of at most 60 items. Bootstrap the sd of a gap before setting a margin (a bar that holds is head at least base minus 2 sd), and never ask a total to move by +1: pass on a seeded `path:line` listed in every run.
- **Hidden mask**: top-down routing, where the judge picks a branch and then grades its children, is a hidden mask with compounding judge error; grade every criterion with the full rubric instead.

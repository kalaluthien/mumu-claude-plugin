# Calibrate

Measure how far a judge's verdicts on a spec can be trusted, and set each tier's judge error from what you measure.

The commands are `${CLAUDE_PLUGIN_ROOT}/skills/card/scripts/measure-judge.py <mode> <spec> …`; each prints what its numbers mean. [spec/model.md](spec/model.md) says why agreement bounds the weights.

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

**Monitor**

During training, watch the signals the spec's monitor lists, and at least these:
- reward rising while held-out expert pairwise wins stay flat: the policy found a gap in the criteria;
- the MET rate of one criterion drifting: the policy learned to satisfy the judge's reading of it;
- answer length trending up: a length bias the perturbation suite missed.

Each one sends the spec to [repair.md](repair.md).

## Rules

- **Counts by a model**: a count a model makes that must repeat within 10% is not asked as a free list, which swings 15-30%. Have code cut the text into numbered sentences (and at `;`) and the model only score each one, three times, keeping the median per sentence. For duplicates, code picks each sentence's 3 nearest by word Jaccard and the model scores each pair 0 or 1, keeping a pair when 2 of 3 runs agree. Ask files in parts of at most 60 sentences, and synonym groups per 40 query terms against the full list. Never reuse or move an output folder of replies while an older run still writes, since stale replies become cache.
- **Seeded defect**: a seeded-defect criterion cannot ask a total to move by +1, since run noise is -7 to +9; pass on the seeded `path:line` listed in 3 of 3 runs and absent from the unseeded runs.
- **Noise first**: bootstrap the sd of a gap before setting a margin ("ahead by 0.1" inside sd 0.06-0.08 never holds); a bar that holds is head at least main minus 2 sd on every dimension. A fix the graders' reasons name moves a criterion; a gap they do not explain is noise.
- **Headroom**: give a criterion headroom by reading the sample for what a criterion lacks before keeping it: "the opening names the parts" gave none, as every page had a contents list, while "the opening says how the parts relate" dropped 8 of 9 from 3. Good anchors drop too, so bound them per criterion by the mean over the set.
- **Fixed key**: a completeness score counts against a fixed key built from the sources, never the gaps a reader raises from the model's own text, which rewards saying less. The key's granularity sets the ceiling (a 218-item key gave every run 7-17%), so size key and bar together.
- **Biases add up**: judge biases within one tier, such as length or wording, add up, and the tier condition does not remove them; the perturbation suite measures them.
- **Hidden mask**: top-down routing, where the judge picks a branch and then grades its children, is a hidden mask with compounding judge error; grade every criterion with the full rubric instead.

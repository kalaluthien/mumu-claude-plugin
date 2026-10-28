# Grade

Apply a rubric to verdicts for one use. Check it first with `check-spec.py check`. The command is `../scripts/score-spec.py`; each mode prints what its result means.

## Steps

### Train

Run `score-spec.py score <spec> <verdicts>`, whose verdict file groups the answers to each prompt. Use each answer's advantage as its reward signal; keep the per-group normalisation, which rescales whichever tier first separates a group. Lower tiers learn mainly from groups the higher tiers tie.

### Eval

Run `score-spec.py compare <spec> <system A verdicts> <system B verdicts> --seed <n>`. Report each system's mean tier vector with its interval, and the verdict the script prints, each delta the indifference band. Never collapse the vector into one number to compare across tasks.

### Human

Make a grading sheet from the rubric: one row per criterion, ordered by tier, each with its text and anchors, and a 0 or 1 to fill in. A masked tier the answer fails ends the sheet for that answer. A pairwise tier becomes a side-by-side comparison of the answers in a group. Turn the filled sheets into a verdict file, then run `score-spec.py order`. With two graders, run `measure-judge.py human` on their two verdict files to see where they disagree: [calibrate.md](calibrate.md).

## Rules

- **Least-bad**: ordinal rewards with mean-centring can reward the least-bad failure; that is what no mask means, so make sure it is intended.

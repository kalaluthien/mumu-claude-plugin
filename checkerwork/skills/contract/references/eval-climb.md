# Climb

Raise one score of a runnable suite by changes kept only when cases the change was not tuned on improve. With no suite that runs and scores, stop and build one ([eval-graders.md](eval-graders.md)).

A climb's files sit in the repo's eval folder, `evals/climb/<name>/`, fed by the runner's own output (`claude plugin eval --json`): `README.md` holds the goal, the split's case ids and one row per round; `baseline/` and `v<N>/` each hold `run.json`, `traces/` (gitignored) and, but baseline, `change.md` (first line the change, then why) and `change.patch`.

## Before round 1

1. Goal: the owner names the score to raise, what may change (a skill's body or description, a prompt, the model or effort) and what may not. Every other number the runner records, cost and turns included, is a guardrail that holds within noise. Show a table of what will change and what will not, and cases × runs × rounds with the minutes one baseline pass took, and wait for a yes.
2. Split: draw once at random, stratified by the case's kind (a trigger's should-fire and near miss), never by baseline score: train, whose transcripts are read, and test, only ever scored. Below about 20 cases, split nothing: raise the runs, read a few failures, and call the result directional.
3. Baseline: run the unchanged plugin over every case at the chosen runs, `--keep-temp`, and copy each trace, since the runner deletes it. Recompute the score from the per-run rows, never from a printed total.
4. Can it move: put three numbers to the owner, the noise floor (a pass rate's 95% half-width is about `1/sqrt(cases × runs)`: 25 × 2 is ±14 points), the headroom (1 minus the baseline) and the smallest gain they would act on; a floor above either calls for more cases or runs first. Disable the mechanism (`--ablation with-without`, or the skill removed): the score must drop. Read the lowest baseline failures and mark each a harness error, excluded from the score, or a grader verdict; fix a wrong grader and regrade before round 1.
5. Answer isolation: what a grader expects stays out of the prompt, the scaffold and the plugin's own files, and a pass whose transcript reads `evals/` is void.

## Each round

1. Analyze: one fresh subagent reads only train's transcripts and rows, names the one behaviour that costs the most train cases, how many and how much, and proposes one change that fixes it at its root, above the noise floor, quoting the train traces behind it. It describes behaviour and never pastes a case's content; a change it expects to regress a case names that case.
2. Apply: cut from the change every platitude and restated default, apply it, and write `v<N>/change.md` and `change.patch`.
3. Run every case at the baseline's runs.
4. Keep the change only when test rises beyond the noise floor and train does not fall; train up and test flat is overfitting, and a guardrail outside noise also reverts it. Add the round's row to `README.md`: round, change, test, train, each guardrail.
5. Stop at the owner's rule: fewer than their smallest gain over three rounds in a row, N rounds, or a check-in each round.

Two or three rounds inside the noise floor: stop changing content and sort each remaining train failure, a fresh subagent reading as in step 1:

| bucket | sign | instead |
| --- | --- | --- |
| artifact gap | the model lacked a fact or rule and guessed | go on climbing |
| grader | the output looks right and failed, or prompt and grader ask different things | fix the grader, regrade every round, and restart from baseline if the order of rounds flips |
| harness | the run died before a scorable output | fix it, excluding those runs meanwhile |
| structure | the fact is in the artifact and was never reached | reorganise: split, route or merge, rather than add text |
| variance | identical runs flip as much as a round moves | report the best so far, offer more runs |

## Report

Test's score at baseline and at the best round, each with its interval, and the delta; a delta within noise is said plainly, with the advice not to merge. Then the round table, train beside test; each applied change with its why; and two or three transcript pairs, one case before and after.

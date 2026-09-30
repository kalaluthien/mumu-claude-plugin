# Judge

A judge grades one failure mode that needs reading, once it has about 20 labelled traces on each side; its numbers are not used until it agrees with the owner. A code grader gets a unit test instead, passing and failing inputs for every condition.

## When

A judge grades a failure mode error analysis found ([analysis-playbook.md](analysis-playbook.md)). Asked for a judge, a score or a metric before that analysis exists, even with a few traces in hand, do not write it: say it would measure a guess no label can check, and start the analysis. A code check of a hard constraint the owner stated ("valid JSON") is the one exception.

## Prompt

1. Task: one mode ("whether the reply quotes a price not in the listing"), never "whether the reply is good".
2. Pass and fail: what each verdict means, with concrete fail examples.
3. Examples: two to four labelled traces from the train split, both verdicts, each critiqued before its verdict.
4. Output: `{"critique": "...", "result": "Pass" | "Fail"}`, enforced by structured output where the provider has it.

One condition per judge: a cheap judge fails correct replies on a criterion of several parts, so split it into one grader each, and make any part a word or pattern decides a `regex`. Give it only the passage the decision needs; pin a capable model to a dated version, and move to a cheaper one only once it agrees as well.

## Validate

1. Label 100 to 200 traces for the mode, so dev and test each hold 30 to 50 of each verdict. With two labellers, measure Cohen's kappa on a shared 20 to 50 and fold each disagreement into the definition.
2. Split once, stratified by label: train 10–20% (the examples), dev 40–45%, test 40–45%.
3. On dev, write `evals/analysis/judge-<mode>.csv` (`trace,human,judge`, each `pass` or `fail`) and run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/contract/scripts/judge-agreement.py <csv>`. Fail is positive: TPR is the share of the owner's fails the judge failed, TNR of passes it passed.
4. Revise from every disagreement until both exceed 90%, sharpening the definition or adding a borderline example; below 80% on either, do not use it. Raise TPR's bar where a miss costs more, TNR's where false alarms flood review, and write the bar beside the mode.
5. Test once on the test split, `judge-<mode>-test.csv`, and report its rates; a revision after seeing them makes test a second dev, and far below dev means relabel a fresh test set.
6. Report a rate over unlabelled traces with the test csv and `--observed <judge pass share> --unlabelled <count>`: it prints the corrected pass rate with a 95% bootstrap interval, or nothing when the judge is near guessing.

Validate again after changing the prompt or the model.

# Validate the judge

Its numbers are not used until it agrees with the owner; a code grader gets a unit test instead, passing and failing inputs for every condition.

1. Label 100 to 200 traces for the mode, so dev and test each hold 30 to 50 of each verdict. With two labellers, measure Cohen's kappa on a shared 20 to 50 and fold each disagreement into the definition.
2. Split once, stratified by label: train 10–20% (the examples), dev 40–45%, test 40–45%.
3. On dev, write `evals/analysis/judge-<mode>.csv` (`trace,human,judge`, each `pass` or `fail`) and run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/contract/scripts/judge-agreement.py <csv>`. Fail is positive: TPR is the share of the owner's fails the judge failed, TNR of passes it passed.
4. Revise from every disagreement until both exceed 90%, sharpening the definition or adding a borderline example; below 80% on either, do not use it. Raise TPR's bar where a miss costs more, TNR's where false alarms flood review, and write the bar beside the mode.
5. Test once on the test split, `judge-<mode>-test.csv`, and report its rates; a revision after seeing them makes test a second dev, and far below dev means relabel a fresh test set.
6. Report a rate over unlabelled traces with the test csv and `--observed <judge pass share> --unlabelled <count>`: it prints the corrected pass rate with a 95% bootstrap interval, or nothing when the judge is near guessing.

Validate again after changing the prompt or the model.

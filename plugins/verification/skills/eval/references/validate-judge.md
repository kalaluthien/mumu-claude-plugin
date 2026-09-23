# Validate the judge

Measure how often an LLM judge agrees with a person, before its numbers are used. A code grader needs a unit test instead.

## 1. Labels and splits

About 100 traces labelled pass or fail for this one mode by the domain expert, roughly half each even if production is skewed: fails are needed to measure the fail side. Two labellers: have both label 20 to 50 of the same traces and settle every disagreement first; disagreement is a vague definition, not noise.

Split once, stratified by label, and never move a trace between splits:

| split | share | used for |
| --- | --- | --- |
| train | 10–20% | the prompt's examples; clear cases only |
| dev | 40–45% | measuring while the prompt is revised |
| test | 40–45% | one final measurement |

## 2. Measure on dev

Run the judge on every dev trace and write `evals/analysis/judge-<mode>.csv` with columns `trace,human,judge`, values `pass` or `fail`. Then:

```sh
python3 <skill dir>/scripts/judge-agreement.py evals/analysis/judge-<mode>.csv
```

It prints the true positive rate (TPR: of the traces a person passed, the share the judge passed) and the true negative rate (TNR: of those a person failed, the share the judge failed). Never report plain accuracy: where most traces pass, a judge that never fails anything scores high on it while missing every defect.

## 3. Revise

Read every disagreement. The judge passed a failure: sharpen the fail definition or add a borderline example. It failed a pass: sharpen the pass definition. Stuck on a group of inputs: add a training example of that group. Both rates stay low: a stronger model, or split the mode into narrower judges. The labels themselves look inconsistent: fix the definition and relabel.

Stop when TPR and TNR both exceed 90%; below 80% on either, do not use the judge.

## 4. Test once

Run the final prompt on the test split once, write `evals/analysis/judge-<mode>-test.csv` in the same columns, and report its rates. Dev rates are optimistic; a revision after seeing test results makes the test split a second dev split.

## 5. Report a rate

A raw pass rate from the judge over unlabelled traces is biased by its errors. Correct it and give an interval:

```sh
python3 <skill dir>/scripts/judge-agreement.py evals/analysis/judge-<mode>-test.csv --observed <judge pass share on unlabelled traces>
```

It prints the corrected rate `(p_obs + TNR − 1) / (TPR + TNR − 1)`, clipped to 0–1, and a 95% bootstrap interval over the test labels. With TPR + TNR near 1 the judge is guessing and no rate is printed. Raising TPR narrows the interval most.

Validate again after changing the prompt or the model, and when the interval widens.

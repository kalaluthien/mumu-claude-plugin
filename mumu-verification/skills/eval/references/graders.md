# Graders

One grader checks one failure mode from `evals/analysis/failure-modes.md` and answers pass or fail. A 1-to-5 scale has no line labellers hold steady, so no agreement can be measured; for degrees of severity, write two binary graders.

## 1. Seed the case

A case's input comes from a trace that showed the mode, trimmed to what reproduces it, and so does its environment: a mode seen in a repo with a given layout reproduces only in that repo. The regression set also holds a case for each core workflow and each known edge case, and gains one per confirmed failure. For a Claude plugin, each case is a folder in the plugin's `evals/` holding a `case.yaml`:

```yaml
schema_version: "1.0"
name: <case>
context:
  scaffold_script: setup.sh   # beside case.yaml; builds the repo the prompt acts on
execution:
  prompt: <the user's prompt>
graders:
  - name: <name>
    type: regex               # an llm grader: type: llm, criteria: <the mode's pass and fail>
    pattern: <pattern>
```

## 2. Code first

Many modes that sound subjective reduce to a word list, a pattern, a parse or an execution. Grade the outcome the user sees, not the path the agent took, unless the path is the defect.

| runner | code graders | judge |
| --- | --- | --- |
| `claude plugin eval` | `regex`, `tool_used`, `tool_order`, `file_exists` | `llm`, its `criteria` the pass and fail |
| promptfoo | `regex`, `javascript`, `python` | `llm-rubric` |

The runner names a bad or missing field when it loads a case.

A `tool_used` grader's tool must be in the case's `allowed_tools`. Under ablation a grader with `arm: with-only` (a `tool_used: Skill` grader is one by default) reports whether the plugin fired instead of scoring, unless it is the case's only grader; give a case at least one grader that scores both arms.

A skill's trigger is decided by its `description` and checked with code: about 20 prompts, half that should fire it and half near misses sharing its words, each a case with a `tool_used: Skill` grader (`min: 1`; for a near miss `min: 0` and `max: 0`), 3 runs each. Tune the description on 60% of them and judge it on the other 40%.

`plugin eval` fires a skill more readily than a live session: confirm a trigger change, and any step moved out of a playbook, live with `claude -p --output-format stream-json`, counting Skill `tool_use` calls before and after.

## 3. A judge, when code cannot

Only for a mode that needs reading to decide, once it has about 20 labelled traces on each side. The prompt has four parts:

1. **Task**: one mode ("whether the reply quotes a price not in the listing"), never "whether the reply is good".
2. **Pass and fail**: the mode's definition as what each verdict means, with concrete fail examples.
3. **Examples**: two to four labelled traces from the train split, both verdicts, each with a critique before its verdict; never one from dev or test.
4. **Output**: `{"critique": "...", "result": "Pass" | "Fail"}`, enforced by structured output where the provider has it (`claude -p --json-schema`, a tool definition).

Give the judge only what the decision needs, cut to the relevant passage; unsure whether a piece helps, remove it and measure on dev again, and leave it out if agreement holds. Start with a capable model pinned to a dated version; move to a cheaper one only once validation shows it agrees as well.

## 4. Validate the judge

Its numbers are not used until it agrees with the owner. A code grader needs a unit test instead: a passing and a failing input for every condition it checks, plus the edge cases error analysis found.

1. **Label**: 100 to 200 traces for this mode, enough that dev and test each hold 30 to 50 of each verdict. One labeller, the owner, is the default. With two, both label 20 to 50 of the same traces independently, measure Cohen's kappa, fold each disagreement into the definition as a rule or an example, and relabel the traces it touches: it is a vague definition, not noise.
2. **Split** once, stratified by label, never moving a trace: train 10–20% (the examples, clear cases), dev 40–45% (revising), test 40–45% (one final measurement).
3. **Measure on dev**: write `evals/analysis/judge-<mode>.csv` (`trace,human,judge`, values `pass` or `fail`) and run:

   ```sh
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/eval/scripts/judge-agreement.py <csv> [--observed <judge pass share>]
   ```

   Fail is the positive class. It prints TPR (of the traces the owner failed, the share the judge failed) and TNR (of those passed, the share the judge passed); plain accuracy hides a judge that never fails anything.
4. **Revise** from every disagreement: a passed failure sharpens the fail definition or adds a borderline example, a failed pass sharpens the pass definition, a stuck input group gets a training example, both rates low call for a stronger model or a narrower mode. Stop when both exceed 90%; below 80% on either, do not use the judge. These bars are defaults: per mode, raise TPR's where a missed failure costs more, TNR's where false alarms flood review, and write the bar beside the mode.
5. **Test once**: run the final prompt on the test split, write `evals/analysis/judge-<mode>-test.csv`, report its rates. A revision after seeing them turns test into a second dev. With test far below dev, the judge overfit dev: revise on dev again, then label a new test set it has never seen.
6. **Report a rate** over unlabelled traces, corrected for the judge's errors: the test csv with `--observed <judge pass share> --unlabelled <trace count>` prints the pass rate `(p_obs + TPR − 1) / (TPR + TNR − 1)`, clipped to 0–1, with a 95% bootstrap interval over both the labels and `p_obs`; with |TPR + TNR − 1| under 0.2 the judge is near guessing and nothing is printed.

Validate again after changing the prompt or the model, and when the interval widens.

# Graders

One grader checks one failure mode from `evals/analysis/failure-modes.md`, and answers pass or fail. A 1-to-5 scale has no line anyone can hold steady: labellers split over neighbouring points, the judge learns their split, and no agreement rate can be measured. For degrees of severity, write two binary graders.

## 1. Seed the case

A case's input comes from a trace that showed the mode, trimmed to what reproduces it. For a Claude plugin:

```
<plugin>/evals/<case>/prompt.md          # frontmatter: max_turns, allowed_tools; body: the user's prompt
<plugin>/evals/<case>/graders/<name>.md  # frontmatter: type and its fields; an llm grader's body is its criterion
```

## 2. Code first

Try code before a judge. Many modes that sound subjective reduce to a word list, a pattern, a parse or an execution. Grade the outcome the user sees, not the path the agent took, unless the path is the defect.

| runner | code graders | judge |
| --- | --- | --- |
| `claude plugin eval` | `regex` (`pattern`, `target`: `last_message`, `trace` or `files`, `match`: `contains`, `not_contains` or `count:N`); `tool_used` (`tool`, `input_match`, `min`, `max`); `tool_order` (`before`, `after`); `file_exists` (`path`, `exists`) | `llm` (body: criterion; `focus`: what it reads); run with `--judge-model` |
| promptfoo | `contains`, `regex`, `is-json`, `javascript`, `python` | `llm-rubric` |

A `tool_used` grader's tool must be in the case's `allowed_tools`. Under ablation a grader with `arm: with-only` (a `tool_used: Skill` grader is one by default) reports whether the plugin fired instead of scoring, unless it is the case's only grader; give a case at least one grader that scores both arms, or the delta measures firing alone.

### A skill's trigger

Whether a skill fires is decided by its `description`, and is checked with code. Write about 20 prompts, half that should fire it and half near misses that share its words but need something else (never an obviously unrelated prompt). Each is a case with a `tool_used: Skill` grader, `min: 1` for the first half and `max: 0` for the second; run each 3 times. When revising the description, tune on 60% of the prompts and judge the result on the other 40%.

## 3. A judge, when code cannot

Write it only for a mode that needs reading to decide, and only once the mode has labelled traces on both sides (about 20 pass and 20 fail). The prompt has four parts:

1. **Task**: what is judged, one mode — "whether the reply quotes a price that is not in the listing", never "whether the reply is good".
2. **Pass and fail**: the mode's definition turned into what each verdict means, with concrete fail examples.
3. **Examples**: two to four labelled traces from the training split ([validate the judge](validate-judge.md) § 1), covering both verdicts plus a case near the line, which teaches the most, each with a written critique before its verdict. Never an example from the dev or test split.
4. **Output**: a critique, then the verdict, as `{"critique": "...", "result": "Pass" | "Fail"}`, enforced by the provider's structured output where it has one (`claude -p --json-schema`, a tool definition).

Give the judge only what the decision needs: the persona and the reply for a tone mode, the retrieved context and the answer for faithfulness, the rules and the reply for instruction following. Cut long documents to the relevant passage; judges are noisy on long inputs.

Start with a capable model and pin its dated version; move to a cheaper one after validation shows it agrees as well.

A judge is not trusted until it is validated: [validate the judge](validate-judge.md).

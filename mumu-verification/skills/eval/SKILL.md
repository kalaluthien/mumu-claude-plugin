---
name: eval
description: Use when a prompt, skill, rubric or model of a Claude plugin or an LLM app changes, when its outputs need judging, or when asked what its evals cover. Not for deterministic code (test).
user-invocable: false
---

# Eval

Find the failure modes in real traces first, then check each with code or with a judge validated against human labels.

Terms and rules: `${CLAUDE_PLUGIN_ROOT}/skills/test/references/contract.md`; read it first. An eval runs cases through an LLM system, each graded pass or fail, and checks a failure mode seen in a trace, never a quality picked in advance ("helpfulness").

| suite | bar |
| --- | --- |
| regression | every run of every case passes its code graders; a drop blocks the change. A judge here gates on its corrected pass rate (Validate the judge, step 6), never on one verdict |
| capability | starts low, a hill to climb; never gates. A case that passes steadily moves to regression |

A suite that has long passed everything catches nothing new: retire its cases or run them less often, and add cases from fresh failures.

## Find what the repo has

| found | runner |
| --- | --- |
| `.claude-plugin/plugin.json` | `claude plugin eval <plugin dir>`, cases in `<plugin>/evals/` |
| `promptfooconfig.yaml`, at the root or in `evals/` | `npx promptfoo eval -c <that file>` |
| another harness in `evals/` or the test runner | use it |

Also look for traces, human labels or notes on them, and judge prompts. With no runner, initialise `evals/` (a plugin: `claude plugin eval init --bare <case>`; an app: `npx promptfoo init --no-interactive evals`) and gitignore its results directory.

Then take the first step that fits, to its end:

| the repo has | step |
| --- | --- |
| a suite, and the question is whether to trust it | audit it: each grader traces to an observed mode, answers pass or fail, and is code where code can decide; each judge has TPR and TNR on a held-out split; each case runs more than once from a clean directory; failing transcripts are read. Report what fails, most harmful first, naming the file and the fix |
| fewer than about 100 traces carrying a person's verdict and note | Error analysis |
| a failure taxonomy, and a mode in it with no check | Graders |
| an LLM judge with no measured agreement with human labels | Validate the judge |
| none of these | Error analysis |

Asked for a judge, a score or a metric before that analysis exists, even with a few traces in hand, do not write it: say it would measure a guess no label can check, and start error analysis. A code check of a hard constraint the owner stated ("valid JSON") is the one exception.

## Error analysis

It writes `evals/analysis/notes.csv` (`trace,verdict,note`) and `evals/analysis/failure-modes.md`.

A trace is the whole run: the input, every tool call, retrieved context and reasoning, and the output. For a plugin, run realistic prompts with `claude plugin eval <dir> --keep-temp --json <file>` and copy each run's `tracePath` into `evals/analysis/traces/`, since it is deleted otherwise; a file the run wrote is the last `Write` for that path in the trace. Or read session transcripts, below. For an app, export its logs or observability tool to JSONL. Sample about 100, some at random and the rest spread across what varies, never the first N; build a small viewer first if the format is hard to read.

With too few real inputs, and someone who can tell a realistic one:

1. Name three axes along which inputs differ and failures are likely; for a skill: the request (names the job, describes the need, a near miss), the repo, the user.
2. Write about 20 tuples, one value per axis; the owner strikes the unrealistic ones.
3. Turn each tuple into a natural input in a separate call, dropping awkward or repeated ones; generate inputs only, and for a skill include ones that should not trigger it.

Open coding: for each trace the owner records a verdict and one note naming the first thing that went wrong, in their words ("quoted a price from the wrong listing", not "hallucination"). Judge an agent's whole run first, single steps only in failed runs. With no owner present, prepare the sample and viewer, say the notes are pending, and stop. After the first ~30 notes the agent may cluster, sample and propose draft verdicts; the owner decides each.

Axial coding: group the notes into failure modes, each with a name, a definition a second person could apply, a count and two or three example traces; merge modes differing only in wording, split one whose examples need different fixes. For a multi-step agent, count failures by the last step that went right and the first that went wrong. Stop when about 20 more traces change nothing, then re-read the first traces.

Sort each mode: a prompt that never asked for the behaviour is fixed in the prompt; asked clearly and not done gets a check, then the fix; a product or tool bug is filed as a bug; rare and cheap, or already fixed, is noted. Rank the rest by frequency and harm (synthetic counts by harm alone), and repeat after a model switch, a prompt rewrite or an incident.

## Graders

One grader checks one mode and answers pass or fail; for degrees of severity, write two binary graders, since a 1-to-5 scale has no line labellers hold steady.

A case's input and environment come from a trace that showed the mode, trimmed to what reproduces it. The regression set also holds a case per core workflow and known edge case, and gains one per confirmed failure. A plugin's case is `evals/<case>/prompt.md`, its front matter the options (`max_turns`, `allowed_tools`, `scaffold_script`) and its body the prompt, with each grader in `graders/<check>.md`, front matter its type and body a judge's pass and fail.

Code first: many modes that sound subjective reduce to a pattern, a parse or an execution. Grade the outcome the user sees, not the path, unless the path is the defect.

| runner | code graders | judge |
| --- | --- | --- |
| `claude plugin eval` | `regex`, `tool_used`, `tool_order`, `file_exists` | `llm` |
| promptfoo | `regex`, `javascript`, `python` | `llm-rubric` |

- An unknown key fails the load, shown as `0 case(s)`: "never used" is `tool_used` with `min: 0` and `max: 0`, and its tool must be in `allowed_tools`.
- Under ablation a `with-only` grader (`tool_used: Skill` by default) reports whether the plugin fired instead of scoring: give each case one grader that scores both arms.
- A skill's trigger is its `description`: about 20 prompts, half that should fire it and half near misses sharing its words, each graded by `tool_used: Skill`, 3 runs each; tune on 60%, judge on 40%. `plugin eval` fires skills more readily than a live session: confirm a trigger change live, counting Skill calls in `claude -p --output-format stream-json`.

A judge, only for a mode that needs reading, once it has about 20 labelled traces on each side. Its prompt has four parts:

1. Task: one mode ("whether the reply quotes a price not in the listing"), never "whether the reply is good".
2. Pass and fail: what each verdict means, with concrete fail examples.
3. Examples: two to four labelled traces from the train split, both verdicts, each critiqued before its verdict.
4. Output: `{"critique": "...", "result": "Pass" | "Fail"}`, enforced by structured output where the provider has it.

Give it only the passage the decision needs; pin a capable model to a dated version, and move to a cheaper one only once it agrees as well.

## Validate the judge

Its numbers are not used until it agrees with the owner; a code grader gets a unit test instead, passing and failing inputs for every condition.

1. Label 100 to 200 traces for the mode, so dev and test each hold 30 to 50 of each verdict. With two labellers, measure Cohen's kappa on a shared 20 to 50 and fold each disagreement into the definition.
2. Split once, stratified by label: train 10–20% (the examples), dev 40–45%, test 40–45%.
3. On dev, write `evals/analysis/judge-<mode>.csv` (`trace,human,judge`, each `pass` or `fail`) and run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/eval/scripts/judge-agreement.py <csv>`. Fail is positive: TPR is the share of the owner's fails the judge failed, TNR of passes it passed.
4. Revise from every disagreement until both exceed 90%, sharpening the definition or adding a borderline example; below 80% on either, do not use it. Raise TPR's bar where a miss costs more, TNR's where false alarms flood review, and write the bar beside the mode.
5. Test once on the test split, `judge-<mode>-test.csv`, and report its rates; a revision after seeing them makes test a second dev, and far below dev means relabel a fresh test set.
6. Report a rate over unlabelled traces with the test csv and `--observed <judge pass share> --unlabelled <count>`: it prints the corrected pass rate with a 95% bootstrap interval, or nothing when the judge is near guessing.

Validate again after changing the prompt or the model.

## Run

```sh
claude plugin validate <plugin dir>
claude plugin eval <plugin dir> --case <case> --runs 3 --trust-plugin --keep-temp
```

- `<plugin dir>` is absolute or `./<dir>`: a bare name runs the installed copy. The run reads it live: edit nothing until it ends, or run a committed copy.
- `--trust-plugin` answers the trust prompt a headless run cannot, for code you have read. One `--case` per call; a `scaffold_script` needs `--scaffold`; a grader of a written file needs `--allow-tools Write`.
- Run each case more than once from a clean directory: regression passes every run, capability once. Read the arms' score delta and the failed transcripts, not only the score: a failure may be the grader's.

## Transcripts

A session's transcript is `~/.claude/projects/<project>/<session>.jsonl`, every turn already recorded:

- A person's prompt has `origin.kind` `human`, another session's `peer`; hook feedback is `isMeta: true`. A compaction is `subtype: compact_boundary`.
- Records are not in time order, since a resume appends: select by `timestamp`, count sessions by `sessionId`. A subagent writes `<session>/subagents/agent-<id>.jsonl`.
- Find which files a session read by their content in tool results, not their paths. Files expire after 30 days by default.
- Tokens: one message spans several records repeating its `usage`, so key on `message.id` and take the maximum `output_tokens`; skip `model: "<synthetic>"` records.

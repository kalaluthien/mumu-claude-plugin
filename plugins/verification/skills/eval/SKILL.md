---
name: eval
description: Use when the project is a Claude plugin or an LLM app and a prompt, a skill, a rubric or a model changed, or its outputs need judging, or asked what its evals cover - finds the failure modes in real traces first, then checks each with code or a judge validated against human labels; not for deterministic code, which a test covers.
---

# Eval

Terms and rules: `${CLAUDE_PLUGIN_ROOT}/contract.md`; read it first. An eval checks a failure mode seen in a trace, never a quality picked in advance ("helpfulness").

| suite | bar |
| --- | --- |
| regression | every run of every case passes; a drop blocks the change |
| capability | starts low, a hill to climb; never gates. A case that passes steadily moves to regression |

A suite that has passed everything for a long time catches nothing new: retire its cases or run them less often, and add cases from fresh failures.

## 1. Find what the repo has

| found | runner |
| --- | --- |
| `.claude-plugin/plugin.json` | `claude plugin eval <plugin dir>`; cases in `<plugin>/evals/` |
| `promptfooconfig.yaml`, at the root or in `evals/` | `npx promptfoo eval -c <that file>` |
| another harness in `evals/` or the test runner | use it |

Also look for traces (logs, transcripts, exported runs), human labels or notes on them, and judge prompts.

If no runner is found, initialise `evals/`: a plugin, `claude plugin eval init --bare <case>` in the plugin directory; an app, `npx promptfoo init --no-interactive evals`. Add the runner's output directory (`evals/results/` for a plugin) to `.gitignore`.

## 2. Take the step the repo is at

Read the file the first matching row names, and follow it to its end before the next.

| the repo has | step |
| --- | --- |
| a suite, and the question is whether to trust it | audit it: each grader traces to an observed mode, answers pass or fail, and is code where code can decide; each judge has TPR and TNR on a held-out split; each case runs more than once from a clean directory; failing transcripts are read. Report what fails, most harmful first, naming the file and the fix |
| fewer than about 100 traces carrying a person's verdict and note | [error analysis](error-analysis.md) |
| a failure taxonomy, and a mode in it with no check | [graders](graders.md) § 1–3 |
| an LLM judge with no measured agreement with human labels | [graders](graders.md) § 4 |

When no row fits, start with error analysis.

Asked for a judge, a score or a metric before that analysis exists — even with a few example traces in hand — do not write it. Say that a grader written now would measure a guess and could not be checked against labels that do not exist, then start error analysis. A handful of traces seeds the analysis; it does not replace it.

## 3. Run

```sh
claude plugin validate <plugin dir>
claude plugin eval <plugin dir> --case <case> --runs 3
```

The first run in a directory asks whether to trust the plugin; a headless session cannot answer, so pass `--trust-plugin` for a plugin whose code you have read. One `--case` per call: a second one replaces the first. A case whose `case.yaml` names a `scaffold_script` needs `--scaffold`, or it runs in an empty directory.

Run each case more than once: the system is not deterministic. For regression, every run must pass (`--threshold 1.0`, the default); for capability, one pass in the runs shows it can. Each run starts from a clean directory; a harness of your own must do the same, or runs that share files or caches fail together.

Read the score delta between the with-plugin and without-plugin arms. A regression case below its bar is a defect in the change. Read the transcripts of failed runs, not only the score: a failure may be the grader's.

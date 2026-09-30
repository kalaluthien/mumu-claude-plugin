# Eval

Find the failure modes in real traces first, then check each with code or with a judge validated against human labels, and move a score only by changes cases they were not tuned on confirm.

An eval runs cases through an LLM system, each graded pass or fail, and checks one failure mode seen in a trace, never a quality picked in advance ("helpfulness"). One eval covers one flow: several flows are several evals.

| suite | bar |
| --- | --- |
| regression | every run of every case passes its code graders; a drop blocks the change. A judge here gates on its corrected pass rate ([eval-judge.md](eval-judge.md), step 6), never on one verdict |
| capability | starts low, a hill to climb; never gates. A case that passes steadily moves to regression |

A suite that has long passed everything catches nothing new: retire its cases or run them less often, and add cases from fresh failures.

## Find what the repo has

| found | runner |
| --- | --- |
| `.claude-plugin/plugin.json` | `claude plugin eval <plugin dir>`, cases in `<plugin>/evals/` |
| `promptfooconfig.yaml`, at the root or in `evals/` | `npx promptfoo eval -c <that file>` |
| another harness in `evals/` or the test runner | use it |

Also look for traces, human labels or notes on them, and judge prompts. With no runner, initialise `evals/` (a plugin: `claude plugin eval init --bare <case>`; an app: `npx promptfoo init --no-interactive evals`) and gitignore its results directory. Never replace a runner the repo has, nor call the model around the app's own entry point.

Then take the first step that fits, to its end:

| the repo has | playbook |
| --- | --- |
| a suite, and the question is whether to trust it | audit it: each grader traces to an observed mode, answers pass or fail, and is code where code can decide; each judge has TPR and TNR on a held-out split; each case runs more than once from a clean directory; failing transcripts are read. Report what fails, most harmful first, naming the file and the fix |
| a runnable suite, and a score to raise: a pass rate, a skill's trigger | [eval-climb.md](eval-climb.md) |
| fewer than about 100 traces carrying a person's verdict and note | [eval-analysis.md](eval-analysis.md) |
| a failure taxonomy, and a mode in it with no check | [eval-graders.md](eval-graders.md) |
| an LLM judge with no measured agreement with human labels | [eval-judge.md](eval-judge.md) |
| none of these | [eval-analysis.md](eval-analysis.md) |

Asked for a judge, a score or a metric before that analysis exists, even with a few traces in hand, do not write it: say it would measure a guess no label can check, and start error analysis. A code check of a hard constraint the owner stated ("valid JSON") is the one exception.

## Run

```sh
claude plugin validate <plugin dir>
claude plugin eval <plugin dir> --case <case> --runs 3 --trust-plugin --keep-temp --no-publish
```

- `<plugin dir>` is absolute or `./<dir>`: a bare name runs the installed copy. The run reads it live: edit nothing until it ends, or run a committed copy.
- `--trust-plugin` answers the trust prompt a headless run cannot, for code you have read. `--no-publish` keeps the report off claude.ai. One `--case` per call; a `scaffold_script` needs `--scaffold`; a grader of a written file needs `--allow-tools Write`.
- Run each case more than once from a clean directory: regression passes every run, capability once. Read the arms' score delta and the failed transcripts, not only the score: a failure may be the grader's.

## Transcripts

A session's transcript is `~/.claude/projects/<project>/<session>.jsonl`, every turn already recorded:

- A person's prompt has `origin.kind` `human`, another session's `peer`; hook feedback is `isMeta: true`. A compaction is `subtype: compact_boundary`.
- Records are not in time order, since a resume appends: select by `timestamp`, count sessions by `sessionId`. A subagent writes `<session>/subagents/agent-<id>.jsonl`.
- Find which files a session read by their content in tool results, not their paths. Files expire after 30 days by default.
- Tokens: one message spans several records repeating its `usage`, so key on `message.id` and take the maximum `output_tokens`; skip `model: "<synthetic>"` records.

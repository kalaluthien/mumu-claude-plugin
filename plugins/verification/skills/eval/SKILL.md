---
name: eval
description: Use when the project is a Claude plugin or an LLM app and a prompt, a skill, a rubric or a model changed - measures the behaviour with eval cases seeded from real failures; not for deterministic code, which a test covers.
---

# Eval

| suite | bar |
| --- | --- |
| regression | stays near 100%; a drop blocks the change |
| capability | a hill to climb; never gates |

## 1. Find what the repo has

| found | runner |
| --- | --- |
| `.claude-plugin/plugin.json` | `claude plugin eval <plugin dir>`; cases in `<plugin>/evals/` |
| `promptfooconfig.yaml` | `npx promptfoo eval` |
| another harness in `evals/` or the test runner | use it |

If none is found, initialise `evals/` for the project's kind, and tell the owner "no eval layout found; initialised `evals/` for <runner>".

## 2. Write a case

Seed cases from real failures: a transcript, a bug report, a wrong answer. One case for a Claude plugin:

```
<plugin>/evals/<case>/prompt.md          # frontmatter: max_turns, allowed_tools; body: the user's prompt
<plugin>/evals/<case>/graders/<name>.md  # frontmatter: type and its fields
```

Graders, cheapest first:

| type | fields | checks |
| --- | --- | --- |
| `regex` | `pattern`, `target`: `last_message` (default), `trace` or `files` | the reply, the trace or the written files match |
| `tool_used` | `tool`, `input_match`, `min` | a tool, e.g. `Skill`, was called |
| `file_exists` | `path`, `exists` | a file was or was not written |
| `llm` | body: the rubric | judgement; add only after about 10 human labels agree with it |

A `tool_used` grader's tool must be in the case's `allowed_tools`.

## 3. Run

```sh
claude plugin validate <plugin dir>
claude plugin eval <plugin dir> --case <case> --runs 3
```

The first run in a directory asks whether to trust the plugin; a headless session cannot answer, so pass `--trust-plugin` for a plugin whose code you have read. One `--case` per call: a second one replaces the first.

Read the score delta between the with-plugin and without-plugin arms. A regression case below its bar is a defect in the change.

# Error analysis

Find how this system fails by reading its traces, before anything is measured. A person judges each trace; the agent samples, records and sorts.

Writes `evals/analysis/notes.csv` (`trace,verdict,note`) and `evals/analysis/failure-modes.md`.

## 1. Gather traces

A trace is the whole run: the input, every intermediate step (tool calls and results, retrieved context, reasoning) and the output. A final answer alone hides where it went wrong.

| system | where traces come from |
| --- | --- |
| Claude plugin or skill | `claude plugin eval <dir> --keep-temp --json <file>` over realistic prompts: each run's `tracePath` in the JSON is its trace, deleted without `--keep-temp`. Or session transcripts in `~/.claude/projects/<project>/*.jsonl` |
| LLM app | its logs or observability tool (Langfuse, Phoenix, Braintrust, LangSmith), exported to JSONL |
| neither | [synthetic inputs](synthetic-inputs.md), run through the system |

Aim for about 100. Sample, never take the first N: some at random, the rest spread across what varies (clusters of inputs, outliers in length, turns, tool calls or latency, traces users complained about).

If the raw format is hard to read (nested JSON, one-line logs), build a small viewer first: one trace per screen, roles distinguished, long tool output collapsed, a pass/fail control and a free-text note. Reading speed decides how many traces get read.

## 2. Open coding

For each trace, the reviewer records a verdict and one note naming the **first** thing that went wrong, in their own words and specific to this product ("quoted a price from the wrong listing", not "hallucination"). A later error is often a consequence of the first; fix that one and the rest may go.

For an agent, judge the whole run against the user's goal first; look at single steps only in the runs that failed.

The reviewer is the person who knows what good looks like for this product: one of them decides, so the standard does not split between labellers. The agent does not write verdicts on a person's behalf. In a run with no person present, prepare the sample and the viewer, say the notes are pending, and stop.

## 3. Axial coding

Group the notes into failure modes. Each mode gets a name, a one-line definition a second person could apply, a count, and two or three example traces. Merge modes that differ only in wording; split one whose examples need different fixes. Recount after every change.

For a multi-step agent, also count where each failure began: a table whose rows are the last step that went right and whose columns are the first that went wrong. The crowded cells are where to look.

Keep reading until about 20 more traces add no new mode and change no definition (saturation). The reviewer's standard shifts as they read (criteria drift): re-read the first traces once the taxonomy settles.

## 4. Sort each mode

| the mode is | next |
| --- | --- |
| a specification failure: the prompt or skill never asked for the behaviour | fix the prompt; no eval needed unless it must never come back |
| a generalisation failure: it was asked for clearly and not done | a check, in [graders](graders.md); then the fix — a stronger model, a smaller task, better context |
| rare and cheap, or already fixed | note it and stop |

Rank the rest by how often and how much it hurts. Re-run this analysis after a model switch, a prompt rewrite or an incident: the modes move.

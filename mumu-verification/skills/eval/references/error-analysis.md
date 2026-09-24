# Error analysis

Find how the system fails by reading its traces, before anything is measured.

Writes `evals/analysis/notes.csv` (`trace,verdict,note`) and `evals/analysis/failure-modes.md`.

## 1. Gather traces

A trace is the whole run: the input, every step between (tool calls and results, retrieved context, reasoning) and the output. A final answer alone hides where it went wrong.

| system | traces |
| --- | --- |
| Claude plugin or skill | `claude plugin eval <dir> --keep-temp --json <file>` over realistic prompts: each run's `tracePath` is its trace, deleted without `--keep-temp`, so copy the traces into `evals/analysis/traces/` first. Or session transcripts in `~/.claude/projects/<project>/*.jsonl` |
| LLM app | its logs or observability tool (Langfuse, Phoenix, Braintrust, LangSmith), exported to JSONL |
| neither, or too few to cover the inputs | synthetic inputs, below, run through the system |

Aim for about 100. Sample, never the first N: some at random, the rest spread across what varies (input clusters, outliers in length, turns, tool calls or latency, complaints).

If the raw format is hard to read, build a small viewer first: one trace per screen, roles distinguished, long tool output collapsed, a pass/fail control and a note field.

### Synthetic inputs

Skip them when about 100 representative real inputs exist, or when nobody can tell a realistic input from an unrealistic one.

1. Name three axes along which inputs differ and failures are likely, each with a few values; for a skill: the request (names the job, describes the need, a near miss), the repo (empty, the expected layout, a competing one), the user (precise, vague, contradictory).
2. Write about 20 tuples, one value per axis; the owner strikes the unrealistic ones; a model proposes more, without duplicates.
3. Turn each tuple into a natural input in a separate call from the one that made it, with one hand-written example. Drop inputs that read awkwardly, miss their tuple or repeat another. Generate inputs only, never outputs; for a skill, include inputs that should not trigger it.

## 2. Open coding

For each trace the owner records a verdict and one note naming the first thing that went wrong, in their words and specific to this product ("quoted a price from the wrong listing", not "hallucination"). A later error is often a consequence of the first.

For an agent, judge the whole run against the user's goal first, and single steps only in the runs that failed.

One person who knows what good looks like decides, so the standard does not split. With no person present, prepare the sample and the viewer, say the notes are pending, and stop.

After the owner's first ~30 notes, the agent may cluster traces, sample them and propose the next to read, with a draft verdict; the owner accepts or rejects each, and the verdict stays the owner's.

## 3. Axial coding

Group the notes into failure modes, each with a name, a one-line definition a second person could apply, a count, and two or three example traces. Merge modes that differ only in wording; split one whose examples need different fixes; recount after each change.

For a multi-step agent, also count where each failure began: rows are the last step that went right, columns the first that went wrong. The crowded cells are where to look.

Stop when about 20 more traces add no mode and change no definition. The owner's standard drifts while reading: re-read the first traces once the taxonomy settles.

## 4. Sort each mode

| the mode is | next |
| --- | --- |
| a specification failure: the prompt never asked for the behaviour | fix the prompt; a check only if it must never return |
| a generalisation failure: asked clearly, not done | a check, in [graders](graders.md); then the fix |
| a product or tool bug (a crash, a broken integration, a missing permission) | file it as a bug; no eval |
| rare and cheap, or already fixed | note it and stop |

Rank the rest by frequency and harm; counts over synthetic inputs reflect the tuples chosen, not prevalence, so rank those by harm alone. Repeat the analysis after a model switch, a prompt rewrite or an incident.

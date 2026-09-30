# Error analysis

It writes `evals/analysis/notes.csv` (`trace,verdict,note`) and `evals/analysis/failure-modes.md`.

## Traces

A trace is the whole run: the input, every tool call, retrieved context and reasoning, and the output. For a plugin, run realistic prompts with `claude plugin eval <dir> --keep-temp --json <file>` and copy each run's `tracePath` into `evals/analysis/traces/`, since it is deleted otherwise; a file the run wrote is the last `Write` for that path in the trace. Or read session transcripts ([eval.md](eval.md) § Transcripts). For an app, export its logs or observability tool to JSONL. Sample about 100, some at random and the rest spread across what varies, never the first N; build a small viewer first if the format is hard to read.

Before pulling production logs, ask whether a retention rule will force their deletion or they hold personal data that cannot sit in the repo; if so, keep only their ids and fetch at run time, or have the owner anonymise a sample.

With too few real inputs, and someone who can tell a realistic one:

1. Take three to five real inputs from the owner, and one sentence on what makes an input hard here: generating from the prompt alone gives inputs simpler than real ones.
2. Name three axes along which those inputs differ and failures are likely; for a skill: the request (names the job, describes the need, a near miss), the repo, the user.
3. Write about 20 tuples, one value per axis; the owner strikes the unrealistic ones.
4. Turn each tuple into a natural input in a separate call, modelled on the real ones, dropping awkward or repeated ones; generate inputs only, and for a skill include ones that should not trigger it.

Show the owner every input, in one markdown file, and go on only after an explicit yes: an unread input set gives a number nobody trusts.

## Coding

Open coding: for each trace the owner records a verdict and one note naming the first thing that went wrong, in their words ("quoted a price from the wrong listing", not "hallucination"). Judge an agent's whole run first, single steps only in failed runs. With no owner present, prepare the sample and viewer, say the notes are pending, and stop. After the first ~30 notes the agent may cluster, sample and propose draft verdicts; the owner decides each.

Axial coding: group the notes into failure modes, each with a name, a definition a second person could apply, a count and two or three example traces; merge modes differing only in wording, split one whose examples need different fixes. For a multi-step agent, count failures by the last step that went right and the first that went wrong. Stop when about 20 more traces change nothing, then re-read the first traces.

Sort each mode: a prompt that never asked for the behaviour is fixed in the prompt; asked clearly and not done gets a check ([eval-graders.md](eval-graders.md)), then the fix; a product or tool bug is filed as a bug; rare and cheap, or already fixed, is noted. Rank the rest by frequency and harm (synthetic counts by harm alone), and repeat after a model switch, a prompt rewrite or an incident.

---
name: drill-it
description: Use when show-me or grill-me needs the facts of a system, a change, data or options found and checked before it draws or asks.
user-invocable: false
context: fork
---

# drill-it

Find and check what an ask rests on, and hand it back; never ask the user and
never draw. The arguments name the settled ask and its purposes, rows of the
table below, in the order the page places them:

$ARGUMENTS

## Procedure

1. Do each purpose's row below.
2. Check each fact as Checked facts says, the cheapest check that can fail first.
3. Hand back as Hand-back says.

| purpose | how |
| --- | --- |
| zoom-diagram | Read the system: code, docs, configs, screens. `${CLAUDE_PLUGIN_ROOT}/skills/drill-it/scripts/check-system.py new system.json` starts a valid system model. Model in the order of [references/model-writing.md](references/model-writing.md), under the plan the caller passed; Alloy's questions are in [references/proof-commands.md](references/proof-commands.md). Run `check-system.py check system.json --quick` after each edit, and the full check once the quick one passes; its `four-states` rule finds each state level's Missing, Illegal, Redundant and Overloaded states. A `finding` line is a defect of the system: report it, and change the model only for your own mistake, where the model misstates what the system does. |
| option-cards | Fix the criteria before naming any option. Count the options: the ones the ask names, and a third only where a real one exists; at least three for an open ask. Two options one sentence argues equally are one idea restyled: replace one. Settle each criterion's value per option, then each option's risk. |
| sitrep | For a change or a text, read it itself: `gh pr view <n> --json title,body,files,headRefOid` and `gh pr diff <n>`, or the text and its history. For numbers or events, get the data with a command (`gh api`, `gh issue list --json`, `git log`, a log), and compute counts, sums and periods with a script. |
| interactive-demo | Name the parameters with their current values and allowed ranges, the cases the reader knows, and the sample the Preview runs on; for steps to follow, each step's exact command, run where it is safe to run. |
| decision | Find, for each open decision the caller names, what the Question shape the caller passed asks for. |

## Constraints

- **Checked facts**: every name, number, status and path under `## Facts` comes from a file read, a command run or a page opened in this run.

## Hand-back

The last message, in English, opens with this line, then holds only these
sections:

> Mark each Not verified item as not verified wherever you use it.

- `## Facts`: one fact per line, then ` — ` and its file and line, command or url.
- `## Not verified`: what the ask needs that no check confirmed, or `none`.
- `## Undecided`: each point the facts leave to the user, with the option you recommend, or `none`.
- `## Findings`: each `finding` line of the last check, with the counterexample's calls, or `none`.
- a section named after each purpose, filling each part the caller passed; for a zoom diagram, the `system.json` path and its last `check` line; for a decision, the Question shape's parts per open decision.

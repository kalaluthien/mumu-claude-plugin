---
name: drill-it
description: Use when show-me or grill-me needs the facts of a system, a change, data or options found and checked before it draws or asks.
user-invocable: false
context: fork
---

# drill-it

Find and check what an ask rests on and hand it back; never ask the user, never draw. Arguments: the settled ask and its purposes (below), in page order:

$ARGUMENTS

## Procedure

Do each purpose, cheapest failing check first, then hand back as Hand-back says.

| purpose | how |
| --- | --- |
| analyse-system | An existing system, under the caller's plan: [references/analyse-system.md](references/analyse-system.md). |
| design-system | A system not yet built, from the caller's intent and plan: [references/design-system.md](references/design-system.md). |
| improve-system | The caller's original `system.json` (analyse first if none): [references/improve-system.md](references/improve-system.md). |
| option-cards | Fix the criteria before naming any option. Count the options: the ones the ask names, and a third only where a real one exists; at least three for an open ask. Two options one sentence argues equally are one idea restyled: replace one. Settle each criterion's value per option, then each option's risk. |
| sitrep | For a change or a text, read it itself: `gh pr view <n> --json title,body,files,headRefOid` and `gh pr diff <n>`, or the text and its history. For numbers or events, get the data with a command (`gh api`, `gh issue list --json`, `git log`, a log), and compute counts, sums and periods with a script. |
| interactive-demo | Name the parameters with their current values and allowed ranges, the cases the reader knows, and the sample the Preview runs on; for steps to follow, each step's exact command, run where it is safe to run. |
| decision | Find, for each open decision the caller names, what the Question shape the caller passed asks for. |

## Constraints

- **Checked facts**: check each fact when you take it; every name, number, status and path under `## Facts` comes from a file read, a command run or a page opened in this run.

## Hand-back

The last message, in English, opens with this line, then only these sections:

> Mark each Not verified item as not verified wherever you use it.

- `## Facts`: one per line, then ` — ` and its file and line, command or url.
- `## Not verified`: what the ask needs that no check confirmed, or `none`.
- `## Undecided`: points left to the user, each with your recommended option, or `none`.
- `## Findings`: defects noted while reading and each `finding` line of the last check, with the counterexample's calls, or `none`; change the model only for your own mistake.
- a section per purpose, filling each part the caller passed; system playbook: each `system.json` path and its last `check` line (`scripts/check-system.py`, whose `rules` lists each check); decision: the Question shape's parts per open decision.

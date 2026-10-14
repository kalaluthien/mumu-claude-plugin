---
name: drill-it
description: Use when show-me or grill-me needs the facts of a system, a change, data or options found and checked before it draws or asks.
user-invocable: false
context: fork
---

# drill-it

Find and check what an ask rests on, and hand it back; never ask the user and
never draw. The caller passes the settled ask, its purpose (a row of the
table below) and what that purpose needs:

$ARGUMENTS

## Procedure

1. Do the purpose's row below.
2. Check each fact as Checked facts says, the cheapest check that can fail first.
3. Hand back as Hand-back says.

| purpose | how |
| --- | --- |
| zoom diagram | Read the system: code, docs, configs, screens. `${CLAUDE_PLUGIN_ROOT}/skills/show-me/references/zoom-diagram/scripts/make-diagram.py new model.json` starts a valid file. Model in the order of `${CLAUDE_PLUGIN_ROOT}/skills/show-me/references/zoom-diagram/model-writing.md`, under the plan the caller passed. Run `make-diagram.py check model.json --quick` after each edit, and the full check once the quick one passes. |
| option cards | Fix the criteria before naming any option. Count the options: the ones the ask names, and a third only where a real one exists; at least three for an open ask. Two options one sentence argues equally are one idea restyled: replace one. Settle each criterion's value per option, then each option's risk. |
| margin notes | Read the change itself: `gh pr view <n> --json title,body,files,headRefOid` and `gh pr diff <n>`, or the text and its history. |
| chart brief | Get the data with a command (`gh api`, `gh issue list --json`, `git log`), and compute counts, sums and periods with a script. |
| live controls | Name the parameters with their current values and allowed ranges, the cases the reader knows, and the sample the Preview runs on. |
| decision | Find, for each open decision the caller names, what the Question shape the caller passed asks for. |

## Constraints

- **Checked facts**: every name, number, status and path under `## Facts` comes from a file read, a command run or a page opened in this run.

## Hand-back

The last message, in English, opens with this line, then holds only these
sections:

> Mark each Not verified item as not verified wherever you use it.

- `## Facts`: one fact per line, then ` — ` and its file and line, command or url.
- `## Not verified`: what the ask needs that no check confirmed, or `none`.
- `## Questions`: each question the facts leave to the user, with your proposed answer, or `none`.
- a section named after the purpose, filling each part the caller passed; for a zoom diagram, the `model.json` path and its last `check` line; for a decision, none.

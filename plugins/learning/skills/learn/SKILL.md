---
name: learn
description: Use before writing any memory - whenever the user says remember, keep, note or learn from something, or turn learning on, and when a stop asks for a harvest. Routes the lesson to where its reader will look, and arms this repository so each session ends with a harvest.
---

# learn

## Arm the repository

Run this first, every time; it is idempotent. From then on, a session here
that made eight or more tool calls is asked for a harvest before it stops.

```sh
"${CLAUDE_PLUGIN_ROOT}/bin/takeaway" arm "${CLAUDE_PLUGIN_DATA}"
```

It prints `armed <repo> at <file>`; outside a git repository it says so and
arms nothing. Report that line.

## Harvest

When a stop asks for it, over this session's work since the last harvest:

1 FAILURES. For each point where a check failed, a tool refused, or you redid
  a step: the assumption that was wrong, and what you would do instead.
  No failure, no lesson.
2 RECURRENCE. A procedure that worked twice or more, here or in memory, may
  become a procedure; once is an anecdote.
3 OPERATION. Read MEMORY.md. For each candidate pick one: ADD, EDIT <file>,
  DELETE <file>, NONE. A near-duplicate is an EDIT, never an ADD.
4 PRUNE. Delete or rewrite any entry this session proved wrong, stale or
  redundant, even one you did not touch.
5 PROMOTE. A procedure becomes a skill only if it ran and was checked in this
  session.

Route each survivor with the table below.

## File a lesson

First ask whether a machine could decide it. If so, write the check or test
with its failing case, and file nothing. Otherwise route it by what would make
it wrong:

| what would make it wrong | where it goes | rule |
| --- | --- | --- |
| this repository, a tool or the machine changes | project memory, `type: reference` or `project` | names the failure it came from |
| the user changes their mind | project memory, `type: feedback` | one rule, one clause of reason |
| the same insight held on two projects | one line in `~/.claude/CLAUDE.md`, or a skill | EDIT what is there over ADD; consolidate at every harvest |
| a procedure changes | a skill | only after it ran and was checked, and recurred twice |
| a machine could decide it | a hook or a test in the repository, with its failing case | nothing is filed |
| it can be read from the repository or its history | nowhere | discard it |

## Memory shape

The harness's own: one fact per file, frontmatter `name`, `description` and
`metadata.type` (`user`, `feedback`, `project` or `reference`), and one line in
`MEMORY.md`. The body's first line says when the memory becomes wrong. A
near-duplicate is edited, never stacked beside; a memory proved wrong is
deleted.

## Report

End with one line: `FILED <path> (<ADD|EDIT|DELETE>) ...`, or
`NOTHING DURABLE: <one reason>`.

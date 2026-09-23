---
name: learn
description: Use before writing any memory - when the user says remember, keep, note or learn from something, or turn learning on - and when a stop asks for a harvest. Files each lesson in auto-memory, memory or a skill, and arms this repository so its sessions end with a harvest.
---

# learn

## Arm

Run this first, every time, and report the line it prints:

```sh
"${CLAUDE_PLUGIN_ROOT}/bin/takeaway" arm "${CLAUDE_PLUGIN_DATA}"
```

## Harvest

Go over the work since the last harvest. For one lesson the user hands you,
start at step 2.

1. Find each surprise: a check that failed, a tool that refused, a step
   redone, or a success by a path you did not plan. Write each as a rule to
   act on at the start of a task: when <situation>, do <action>, because <the
   assumption it broke>. Keep a name, path or value only if the rule is about
   it.
2. Search every project's auto-memory, `~/.claude/projects/*/memory/`, for
   the same lesson. Pick the last row of the table below that it fits, and
   read what is there now.
3. Apply one operation to one entry: ADD, EDIT <entry>, DELETE <entry>, or
   NONE when it is already said. A near-duplicate is an EDIT; a lesson
   promoted to a later row DELETEs the entries it replaces. Never rewrite a
   file to fold a lesson in.
4. Delete or correct any entry this session showed wrong, touched or not.

End with one line: `FILED <path> (<op>) ...`, or `NOTHING DURABLE: <reason>`.

## Destinations

| the lesson | destination | shape |
| --- | --- | --- |
| holds for this project: a fact, a trap, the user's preference, a procedure that worked once | auto-memory, the directory the harness names | one fact per file, as the harness's memory instructions give it |
| another project's auto-memory already holds it, or the user gave it for all work | memory: `~/.claude/CLAUDE.md` | one instruction and one clause of reason, in the section naming the work |
| is a procedure auto-memory already holds, and it has now worked again | the skill that owns the work, edited in its source and never under `~/.claude/plugins/cache/`, or a new one in `~/.claude/skills/` | the steps as run, what varied between runs as parameters, a description saying when to use it |

File nothing a check could decide: write the check with its failing case.
File nothing the repository or its history already states.

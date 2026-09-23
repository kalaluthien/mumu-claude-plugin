---
name: learn
description: Use when writing or editing a SKILL.md, a hook or its script, or an agents/*.md file, and when something learned should outlive the session - a memory, learning turned on, a stop's harvest. Not for settings.json permissions or env (update-config).
---

# learn

To write or edit a skill, an agent or a hook with no lesson behind it, skip
Arm and Harvest and follow the reference its row under Destinations links.

## Arm

Run this first, every time but the no-lesson case above, and report the line
it prints:

```sh
"${CLAUDE_PLUGIN_ROOT}/bin/takeaway" arm "${CLAUDE_PLUGIN_DATA}"
```

## Harvest

Go over the work since the last harvest. For one lesson the user hands you,
start at step 2.

1. Find each lesson. A surprise is a check that failed, a tool that refused,
   a step redone, or a success by a path you did not plan; write it as a rule
   to act on at the start of a task: when <situation>, do <action>, because
   <the assumption it broke>, keeping a name, path or value only if the rule
   is about it. A procedure is several steps that worked, which you had to
   work out or took from auto-memory; keep the steps as run.
2. Search every project's auto-memory, `~/.claude/projects/*/memory/`, for
   the same lesson. Pick the last row of the table below that it fits, and
   read what is there now.
3. Apply one operation to each entry you touch: ADD, EDIT <entry>, DELETE
   <entry>, or NONE when it is already said. A near-duplicate is an EDIT. A
   lesson promoted to a later row DELETEs the entries it replaces in this
   project's auto-memory, and leaves other projects' entries alone. Never
   rewrite a file to fold a lesson in.
4. Delete or correct any entry this session showed wrong, touched or not.

End with one line: `FILED <path> (<op>) ...`, or `NOTHING DURABLE: <reason>`.

## Destinations

| the lesson | destination | shape |
| --- | --- | --- |
| holds for this project: a fact, a trap, the user's preference, a procedure that worked once | auto-memory, the directory the harness names | one fact per file, as the harness's memory instructions give it |
| another project's auto-memory already holds it, or the user gave it for all work | memory: `~/.claude/CLAUDE.md` | one instruction and one clause of reason, in the section naming the work |
| is a procedure auto-memory already holds, and it has now worked again | the skill that owns the work, edited in its source and never under `~/.claude/plugins/cache/`, or a new one in `~/.claude/skills/` | the steps as run, what varied between runs as parameters; [skill-authoring.md](references/skill-authoring.md) |
| is how a delegate should work | its `agents/<name>.md` | [skill-authoring.md](references/skill-authoring.md) |
| is something a check could decide | a script or hook, with its failing case, and nothing filed | [hook-authoring.md](references/hook-authoring.md) |

File nothing the repository or its history already states.

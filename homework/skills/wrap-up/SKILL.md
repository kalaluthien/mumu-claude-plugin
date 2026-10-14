---
name: wrap-up
description: Use when a wrap-up signal arrives, or to keep a lesson (retro), tidy memory (dream), or write a skill or hook.
---

# wrap-up

Close a stretch of work so the next session starts ahead: keep what this
session learned (retro), tidy what earlier sessions kept (dream), and record how to run and
verify the repository.

## Vocabulary

- **Signal**: the Stop hook's sentence opening `Wrap-up signal:`, carrying lesson points `<p>` of threshold `<t>`, memory files changed `<m>` of limit `<l>`, and run recipe `<r>`: `fine`, `missing` or `failed`. With none in sight, print this session's: `"${CLAUDE_PLUGIN_ROOT}/hooks/wrap-up-signal.py" ${CLAUDE_SESSION_ID}`.
- **Memory**: what loads into an agent before it acts: instruction files (`AGENTS.md`, `CLAUDE.md`), auto-memory, whose `MEMORY.md` index loads at start and each file only when read, and project skills, whose descriptions load at start.
- **Memory file**: one lesson, then a `When it applies:` line, the situation that should recall it, and a `When it is wrong:` line, the condition that would make it false; its index line is `- [<title>](<file>.md) — <when it applies>`, since only the index is read before the situation arises.
- `<skill>` is `${CLAUDE_SKILL_DIR}`, `<data>` is `${CLAUDE_PLUGIN_DATA}`, and `<config>` is the folder the owner names, else `${CLAUDE_CONFIG_DIR:-$HOME/.claude}`.

## Route

Take every row whose condition holds, in order, and copy its playbook's steps
verbatim into the todo list, a step not done staying as `skip: <reason>`.

| when | playbook |
| --- | --- |
| `<p>` reaches `<t>`, or a person asks to keep a lesson | [references/retro.md](references/retro.md) |
| `<r>` is `missing` or `failed` | [references/run-recipe.md](references/run-recipe.md) |
| `<m>` reaches `<l>`, or a person asks to tidy memory | [references/dream-how.md](references/dream-how.md), over the targets of [references/dream-what.md](references/dream-what.md) |
| writing or editing a skill or an agent file, with no lesson behind it | [references/skill-authoring.md](references/skill-authoring.md) |
| writing or editing a hook or a script, with no lesson behind it | [references/hook-authoring.md](references/hook-authoring.md) |
| typed with no signal and no row fits | [references/retro.md](references/retro.md) |

## Rules

- **No waiting**: ask the owner nothing; file, fix or leave each item for the owner, and report.
- **Repository first**: file nothing the repository or its history already states, and change a repository's file only the way it takes changes, as its `AGENTS.md` says.
- **Outcome**: when the hook asked, end with `"${CLAUDE_PLUGIN_ROOT}/hooks/wrap-up-signal.py" outcome "${CLAUDE_PLUGIN_DATA}" ${CLAUDE_SESSION_ID} filed` if anything was filed, fixed or recorded, else the same with `empty`, so the hook asks less often after empty wrap-ups.

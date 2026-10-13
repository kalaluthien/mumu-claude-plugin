---
name: wrap-up
description: Use when the Stop hook sends a wrap-up signal, or to keep what a session learned or tidy memory.
---

# wrap-up

Close a stretch of work so the next session starts ahead: keep what this
session learned, tidy what earlier sessions kept, and record how to run and
verify the repository.

## Vocabulary

- **Signal**: the Stop hook's sentence, `Wrap-up signal: <f> failed tool calls and <c> tool calls since the last stop make <p> lesson points of <t>; <m> memory files changed since the last tidy, of <l>; run recipe: <r>`, then `, to record with /run-skill-generator` when `<r>` is not `fine`. With none in sight, print this session's: `"${CLAUDE_PLUGIN_ROOT}/hooks/wrap-up-signal.py" ${CLAUDE_SESSION_ID}`.
- **Memory**: what loads into an agent before it acts: instruction files (`AGENTS.md`, `CLAUDE.md`), auto-memory, whose `MEMORY.md` index loads at start and each file only when read, and project skills, whose descriptions load at start.
- **Memory file**: one lesson, then a `When it applies:` line, the situation that should recall it, and a `When it is wrong:` line, the condition that would make it false; its index line is `- [<title>](<file>.md) — <when it applies>`, since only the index is read before the situation arises.
- `<skill>` is `${CLAUDE_SKILL_DIR}`, `<data>` is `${CLAUDE_PLUGIN_DATA}`, and `<config>` is the folder the owner names, else `${CLAUDE_CONFIG_DIR:-$HOME/.claude}`.

## Route

Take every row whose condition holds, in order, and copy its playbook's steps
verbatim into the todo list, a step not done staying as `skip: <reason>`.

| when | playbook |
| --- | --- |
| `<p>` reaches `<t>`, or a person asks to keep a lesson | [references/harvest.md](references/harvest.md) |
| `<r>` is `missing` or `failed` | [references/run-recipe.md](references/run-recipe.md) |
| `<m>` reaches `<l>`, or a person asks to tidy memory | [references/tidy-how.md](references/tidy-how.md), over the targets of [references/tidy-what.md](references/tidy-what.md) |
| typed with no signal and no row fits | [references/harvest.md](references/harvest.md) |

## Rules

- **No waiting**: ask the owner nothing; file, fix or leave each item for the owner, and report.
- **Repository first**: file nothing the repository or its history already states, and change a repository's file only the way it takes changes, as its `AGENTS.md` says.
- **Outcome**: when the hook asked, end with `"${CLAUDE_PLUGIN_ROOT}/hooks/wrap-up-signal.py" outcome "${CLAUDE_PLUGIN_DATA}" filed` if anything was filed, fixed or recorded, else the same with `empty`, so the hook asks less often after empty wrap-ups.

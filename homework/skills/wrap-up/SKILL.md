---
name: wrap-up
description: Use when a wrap-up signal arrives, or to keep a lesson (retro), tidy memory (dream), or write a skill, agent file, hook or script.
user-invocable: false
---

# wrap-up

Close a stretch of work so the next session starts ahead: keep what this session learned (retro), and tidy what earlier sessions kept (dream).

## Domain

- **Signal**: the Stop hook's sentence opening `Wrap-up signal:`, carrying lesson points `<p>` of threshold `<t>`, this session's first retro `<f>`: `due`, `asked` or `at <n> of <limit> tool calls`, and memory files changed `<m>` of limit `<l>`. With none in sight, print this session's: `"${CLAUDE_PLUGIN_ROOT}/hooks/signal-wrap-up.py" ${CLAUDE_SESSION_ID}`.
- **Memory**: what loads into an agent before it acts: instruction files (`AGENTS.md`, `CLAUDE.md`), auto-memory, whose `MEMORY.md` index loads at start and each file only when read, and project skills, whose descriptions load at start.
- **Memory file**: one lesson, then a `When it applies:` line, the situation that should recall it, and a `When it is wrong:` line, the condition that would make it false. Its index line is `- [<title>](<file>.md) — <when it applies>`, since only the index is read before the situation arises.
- `<skill>` is `${CLAUDE_SKILL_DIR}`, `<data>` is `${CLAUDE_PLUGIN_DATA}`, and `<config>` is the folder the owner names, else `${CLAUDE_CONFIG_DIR:-$HOME/.claude}`.

## Route

Take every row whose condition holds, in order, and copy its playbook's steps verbatim into the todo list, a step not done staying as `skip: <reason>`.

| when | playbook |
| --- | --- |
| `<p>` reaches `<t>`, this session's first retro `<f>` is `due`, or a person asks to keep a lesson | [references/retro.md](references/retro.md) |
| `<m>` reaches `<l>`, or a person asks to tidy memory | [references/dream.md](references/dream.md) |
| `python3 ${CLAUDE_SKILL_DIR}/scripts/list-sessions.py due <data>/dejavu` prints `due`, or a person asks for `dejavu` | [references/dejavu.md](references/dejavu.md) |
| writing or editing a skill, an agent file, a hook or a script, with no lesson behind it | [references/harness-authoring.md](references/harness-authoring.md) |
| typed with no signal and no row fits | [references/retro.md](references/retro.md) |

## Rules

- **No waiting**: ask the owner only whether to file an issue, since filing one asks first; do each other step yourself, a slash command only a person types too, by `herdr agent prompt $HERDR_PANE_ID "/<command> <args>"` to the session's own pane, else by `pane send-text` then `send-keys enter` when herdr refuses the pane or the command does not run (`/reload-plugins` did not); leave the owner only what no tool can do, and report.
- **This project only**: write only this project's auto-memory. A change to `<config>/CLAUDE.md`, another project's memory, a hook, a script or a skill goes as a patch file the person applies, the report naming its `!` command, as [references/retro.md](references/retro.md) step 4 says.
- **Repository first**: file nothing the repository or its history already states, and change a repository's file only the way it takes changes, as its `AGENTS.md` says.
- **Outcome**: when the hook asked, end with `"${CLAUDE_PLUGIN_ROOT}/hooks/signal-wrap-up.py" outcome "${CLAUDE_PLUGIN_DATA}" ${CLAUDE_SESSION_ID} filed` if anything was filed, fixed or recorded, else the same with `empty`, so the hook asks less often after empty wrap-ups.

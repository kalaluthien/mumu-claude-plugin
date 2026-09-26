# Agents

Every live session loads these plugins straight from this checkout, so they see a merge once the lead's `clean` pulls it.

## After a merge

After `clean` pulls a merged PR, the lead maps the PR's changed paths (`gh pr diff <pr> --name-only`) to what refreshes them, and does the strongest step any path needs; each `herdr agent prompt` below, succession's included, is one `herdr agent prompt <literal-name> "<text>"` Bash call per agent, no loop and no variable, so `Bash(herdr agent prompt *)` matches it:

| changed path | takes effect | step |
| --- | --- | --- |
| `*/bin/*`, `*/scripts/*`, `*/references/*.md`, the lead's and worker's changing rules included (`mumu-team/skills/kickoff/references/`: the playbooks) | at once | none: `mumu-team/scripts/reread.py`, a `UserPromptSubmit` hook, tells each session that read a changed references file to read it again at its next prompt |
| `mumu-team/lib/*.py`, `mumu-team/scripts/team-watch.py` | when the monitor starts again | `herdr agent prompt <literal-name> "stop your team-watch task and arm the command the Stop hook names"` for each lead in `herdr agent list` |
| `*/skills/*/SKILL.md` (body or list), `*/hooks/hooks.json`, `*/agents/*.md` used as a subagent | `/reload-plugins` | `herdr agent prompt <literal-name> "/reload-plugins"` for each agent in `herdr agent list` |
| `*/agents/*.md` a session runs as (`--agent`: `lead.md`, `worker.md`), a body of only its role, what it never does and when to read each references file | a new session | below |

Succession: each lead hands itself over on its own, prompted `hand yourself over` once its `agent_status` in `herdr agent list` is `idle`, which its body routes to succession, and its successor takes over under the same name ([lead-goal.md](mumu-team/skills/kickoff/references/lead-goal.md)'s Succession). A working session and every worker are left until they finish; the lead that ran `clean` hands over last.

## Plugin layout

Before adding or moving a file in any plugin, read [plugin-authoring.md](mumu-compounding/lib/plugin-authoring.md): where each file sits and how one links another. mumu-team's scripts run `herdr` or `gh` only through its `lib/` module.

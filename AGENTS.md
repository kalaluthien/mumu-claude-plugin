# Agents

Every live session loads these plugins straight from this checkout, so they see a merge once the lead's `clean` pulls it.

## After a merge

After `clean` pulls a merged PR, the lead maps the PR's changed paths (`gh pr diff <pr> --name-only`) to what refreshes them, and does the strongest step any path needs; each `herdr agent prompt` below, succession's included, is one `herdr agent prompt <literal-name> "<text>"` Bash call per agent, no loop and no variable, so `Bash(herdr agent prompt *)` matches it:

| changed path | takes effect | step |
| --- | --- | --- |
| `*/bin/*`, `*/scripts/*`, `*/references/*.md`, the lead's and worker's changing rules included (`mumu-team/skills/kickoff/references/`: routing, planning, folder leads, small change, subagents, playbooks) | at once | none: `mumu-team/scripts/reread.py`, a `UserPromptSubmit` hook, tells each session that read a changed references file to read it again at its next prompt |
| `mumu-team/lib/*.py`, `mumu-team/scripts/team-watch.py` | when the monitor starts again | `herdr agent prompt <literal-name> "stop your team-watch task and arm the command the Stop hook names"` for each lead in `herdr agent list` |
| `*/skills/*/SKILL.md` (body or list), `*/hooks/hooks.json`, `*/agents/*.md` used as a subagent | `/reload-plugins` | `herdr agent prompt <literal-name> "/reload-plugins"` for each agent in `herdr agent list` |
| `*/agents/*.md` a session runs as (`--agent`: `lead.md`, `worker.md`), a body of only its role, what it never does and when to read each references file | a new session | below |

Succession: each lead hands itself over on its own, prompted `hand yourself over` once its `agent_status` in `herdr agent list` is `idle`, which its body routes to succession, and its successor takes over under the same name ([succession.md](mumu-team/skills/kickoff/references/succession.md)). A working session and every worker are left until they finish; the lead that ran `clean` hands over last.

## mumu-team layout

A file sits where [Anthropic's standard layout](https://code.claude.com/docs/en/plugins-reference#standard-layout) and this table say. A script is named in lowercase words joined by `-` for what it does or prints, never a verdict, state or measurement, with its language extension.

| file | goes in |
| --- | --- |
| command a document, `~/.claude/settings.json` or another plugin names bare | `bin/<name>`, on the Bash tool's `PATH` |
| hook or monitor command | `scripts/<name>.py`, run from `hooks/hooks.json` or `monitors/monitors.json` through `${CLAUDE_PLUGIN_ROOT}/scripts/` |
| script only one skill runs | `skills/<skill>/scripts/<name>.py`, run by that `SKILL.md` through `${CLAUDE_PLUGIN_ROOT}` |
| module scripts import | `lib/<noun>.py`, each doing one thing (`command`, `herdr`, `gh`, `names`); a script runs `herdr` or `gh` only through it and imports no other script |
| test | `tests/test_<name>.py`, named after the file or folder it checks, `-` as `_` |
| eval case | `evals/<case>/prompt.md` and `graders/<check>.md`, no `case.yaml` |

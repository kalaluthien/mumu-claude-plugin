# Agents

Every live session loads these plugins straight from this checkout, so they see a merge once the lead's `clean` pulls it.

## After a merge

After `clean` pulls a merged PR, the lead maps the PR's changed paths (`gh pr diff <pr> --name-only`) to what refreshes them, and does the strongest step any path needs:

| changed path | takes effect | step |
| --- | --- | --- |
| `*/bin/*`, `*/references/*.md` | at once | none |
| `mumu-team/lib/team.py`, `mumu-team/bin/team-watch.py` | when the monitor starts again | `herdr agent prompt <pane> "stop your team-watch task and arm the command the Stop hook names"` for each lead in `herdr agent list` |
| `*/skills/*/SKILL.md` (body or list), `*/hooks/hooks.json`, `*/agents/*.md` used as a subagent | `/reload-plugins` | `herdr agent prompt <pane> "/reload-plugins"` for each agent in `herdr agent list` |
| `*/agents/*.md` a session runs as (`--agent`: `lead.md`, `worker.md`) | a new session | below |

Succession, for each lead in `herdr agent list` whose `agent_status` is `idle`: `prompt` it `/mumu-team:kickoff succession`, and its successor takes over ([succession.md](mumu-team/skills/kickoff/references/succession.md)). A working session and every worker are left until they finish; this lead hands over last.

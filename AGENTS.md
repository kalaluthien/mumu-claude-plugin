# Agents

Every live session loads these plugins straight from this checkout, so they see a merge once the lead's `clean` pulls it.

## After a merge

After `clean` pulls a merged PR, the lead maps the PR's changed paths (`gh pr diff <pr> --name-only`) to what refreshes them, and does the strongest step any path needs:

| changed path | takes effect | step |
| --- | --- | --- |
| `*/bin/*`, `*/references/*.md` | at once | none |
| `mumu-team/lib/team.py`, `mumu-team/bin/worker-watch.py`, `mumu-team/bin/lead-heartbeat.py` | at a monitor's restart | `herdr agent prompt <pane> "stop your worker-watch and lead-heartbeat tasks, rerun ensure-monitors.py, and arm what it prints"` for each lead in `herdr agent list` |
| `*/skills/*/SKILL.md` (body or list), `*/hooks/hooks.json`, `*/agents/*.md` used as a subagent | `/reload-plugins` | `herdr agent prompt <pane> "/reload-plugins"` for each agent in `herdr agent list` |
| `*/agents/*.md` a session runs as (`--agent`: `lead.md`, `worker.md`) | restart | below |

Restart, for each lead in `herdr agent list` whose `agent_status` is `idle`: `prompt` it to comment a handoff on its parent issue (with no goal, none) and stop; then `/exit` it and start it again as `<repo>-lead` with the flags `ps -o args= -p <pid>` showed, prompted `/mumu-team:kickoff continue`. A working session and every worker are left until they finish; this lead restarts last, through the owner.

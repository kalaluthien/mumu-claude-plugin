# herdr, for the leader

Guard every command that drives a pane with `test "${HERDR_ENV:-}" = 1`, and name the target explicitly.

| step | command |
| --- | --- |
| who is live | `herdr agent list` (JSON; `name`, `pane_id`, `agent_status`, `cwd`) |
| worktree | `git -C <checkout> fetch origin && git -C <checkout> worktree add --detach <checkout>/.claude/worktrees/<issue>-<topic> origin/<default>`; not `claude -w`, whose isolation guard refuses every git call the RTK hook rewrites |
| new pane | `herdr tab create --cwd <worktree> --label <issue>-<topic>`; the result's pane id is the target |
| start worker | `herdr agent start w<issue>-<topic> --kind claude --pane <pane> -- --model opus --effort <e>` |
| name | herdr refuses an agent name that starts with a digit, hence the `w` |
| brief it | `herdr agent prompt <pane> "work <issue-url>"` (never on the start line) |
| read it once | `herdr agent read <pane>`; answer a folder-trust dialog with `herdr agent send-keys <pane> enter` |
| prompt it | `herdr agent prompt <pane> "<text>"` |
| relaunch | new pane in the same worktree, start with `-- --continue --model opus --effort <e>`, prompt `work <issue-url>` |
| close | `herdr tab close <tab>` after the worker exited |

Statuses: `blocked` is a permission prompt only the owner clears; `idle` also covers a dialog or a usage-limit menu, so read the pane before concluding anything.

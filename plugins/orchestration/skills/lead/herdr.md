# herdr, for the leader

Guard every command that drives a pane with `test "${HERDR_ENV:-}" = 1`, and name the target explicitly.

| step | command |
| --- | --- |
| who is live | `herdr agent list` (JSON; `name`, `pane_id`, `agent_status`, `cwd`) |
| new pane | `herdr tab create --cwd <checkout> --label <issue>-<topic>`; the result's pane id is the target |
| start worker | `herdr agent start <issue>-<topic> --kind claude --pane <pane> -- -w <issue>-<topic> --model opus --effort <e>` |
| brief it | `herdr agent prompt <pane> "work <issue-url>"` (never on the start line) |
| read it once | `herdr agent read <pane>`; answer a folder-trust dialog with `herdr agent send-keys <pane> enter` |
| prompt it | `herdr agent prompt <pane> "<text>"` |
| relaunch | new pane in the worktree `<checkout>/.claude/worktrees/<issue>-<topic>`, start `claude --continue` there, prompt `work <issue-url>` |
| close | `herdr tab close <tab>` after the worker exited |

Statuses: `blocked` is a permission prompt only the owner clears; `idle` also covers a dialog or a usage-limit menu, so read the pane before concluding anything.

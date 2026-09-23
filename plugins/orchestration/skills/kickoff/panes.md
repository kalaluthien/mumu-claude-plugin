# Panes: herdr

Every command names its target pane.

| verb | command |
| --- | --- |
| your address | `$HERDR_PANE_ID` |
| `live` | `herdr agent list`, whose JSON gives each agent's `pane_id`, `tab_id` and `agent_status` |
| `start` | `herdr tab create --cwd <worktree> --label <topic>-<issue>` gives the pane; then `herdr agent start <topic>-<issue> --kind claude --pane <pane> -- --model opus --effort <effort>`, adding `--continue` to resume; then `herdr agent read <pane>` once, and answer a folder-trust dialog with `herdr agent send-keys <pane> enter` |
| `prompt` | `herdr agent prompt <pane> "<text>"` |
| `close` | `herdr agent prompt <pane> "/exit"`, then `herdr tab close <tab>` once `live` no longer lists it |

`blocked` is a permission prompt only the owner clears; `idle` also covers a dialog or a usage-limit menu, so `herdr agent read <pane>` before concluding anything.

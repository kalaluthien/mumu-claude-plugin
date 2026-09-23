# Panes: herdr

Every command names its target pane.

| verb | command |
| --- | --- |
| `ready` | `$HERDR_PANE_ID` is set, and `herdr integration status` has no `claude: not installed` line; without both no session can be addressed or report its state. The fix is to run inside herdr, and `herdr integration install claude` |
| your address | `$HERDR_PANE_ID` |
| `live` | `herdr agent list`, whose JSON gives each agent's `pane_id`, `tab_id` and `agent_status` |
| `start` | `herdr tab create --cwd <worktree> --label <topic>-<issue>` gives the pane; then `herdr agent start <topic>-<issue> --kind claude --pane <pane> -- --model opus --effort <effort>`, adding `--continue` to resume; then `herdr agent read <pane>` once, and answer a folder-trust dialog with `herdr agent send-keys <pane> enter` |
| `watch` | `herdr agent wait <pane> --until blocked`, run in the background; it returns at a permission prompt, or with an error once the agent is gone |
| `prompt` | `herdr agent prompt <pane> "<text>"` |
| `close` | `herdr agent prompt <pane> "/exit"`, then `herdr tab close <tab>` once `live` no longer lists it |

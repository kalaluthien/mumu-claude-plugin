# Panes: herdr

Every command names its target pane.

| verb | command |
| --- | --- |
| `ready` | `$HERDR_PANE_ID` is set, and `herdr integration status` has no `claude: not installed` line; without both no session can be addressed or report its state. The fix is to run inside herdr, and `herdr integration install claude` |
| your address | `<your name>@$HERDR_PANE_ID` |
| `live` | `herdr agent list`, whose JSON gives each agent's `pane_id`, `tab_id` and `agent_status` |
| `start` | `herdr tab create --cwd <worktree> --label <name>` gives the pane; then `herdr agent start <name> --kind claude --pane <pane> -- --name <name> --model opus --effort <effort>`, adding `--continue` to resume; then `herdr agent read <pane>` once, and answer a folder-trust dialog with `herdr agent send-keys <pane> enter` |
| `name` | this session's three names: `herdr tab rename <tab> <name>`, the tab being `herdr pane get $HERDR_PANE_ID`'s `tab_id`; `herdr agent rename $HERDR_PANE_ID <name>`; and `herdr agent prompt $HERDR_PANE_ID "/rename <name>"`, which applies when the turn ends |
| `prompt` | `herdr agent prompt <pane> "<text>"`; when it fails, `SendMessage` the text to the session's name, found with `ListAgents`; say which of the two delivered it |
| `close` | `herdr agent prompt <pane> "/exit"`, then `herdr tab close <tab>` once `live` no longer lists it |

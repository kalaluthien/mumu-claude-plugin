# Panes: herdr

Every command names its target pane.

| verb | command |
| --- | --- |
| `ready` | `$HERDR_PANE_ID` is set, and `herdr integration status` has no `claude: not installed` line; without both no session can be addressed or report its state. The fix is to run inside herdr, and `herdr integration install claude` |
| your address | `<your name>@$HERDR_PANE_ID` |
| `live` | `herdr agent list`, whose JSON gives each agent's `pane_id`, `tab_id` and `agent_status` |
| `start` | `worker-start.py <checkout> <name> <effort> [--continue] [--prompt <text>]`: adds or reuses the worktree `<checkout>/.claude/worktrees/<name>`, opens its tab, starts Claude at that effort, answers the folder-trust dialog, sends the prompt, and prints `<name>@<pane> <worktree>` |
| `name` | this session's three names: `herdr tab rename <tab> <name>`, the tab being `herdr pane get $HERDR_PANE_ID`'s `tab_id`; `herdr agent rename $HERDR_PANE_ID <name>`; and `herdr agent prompt $HERDR_PANE_ID "/rename <name>"`, which applies when the turn ends |
| `prompt` | `herdr agent prompt <pane> "<text>"`; when it fails and the text is a `see <url>` notice, `SendMessage` it to the session's name, found with `ListAgents`; say which of the two delivered it; a failed slash command is not sent that way but retried by herdr, else told to the owner. Success is printed before delivery, and a busy pane or an open dialog can swallow the text: read the pane before and after, resend when no turn carries it, and address by name, since a remembered pane id can be stale |
| `start-lead` | a started lead's cwd is the target checkout's root, never a worktree, and its name `<repo>-lead`, `<repo>` from `gh repo view --json name -q .name` run in that root: `herdr tab create --cwd <root> --label <repo>-lead` gives the pane; then `herdr agent start <repo>-lead --kind claude --pane <pane> -- --name <repo>-lead --model opus --effort medium`, and `prompt` it |
| `broadcast` | `prompt` each agent in `herdr agent list` whose name ends in `-lead`, but you, `see <url>` |
| `close` | `herdr agent prompt <pane> "/exit"`, then `herdr tab close <tab>` once `live` no longer lists it; a running background task stops `/exit` at a dialog, whose option 2 leaves a session herdr does not list |

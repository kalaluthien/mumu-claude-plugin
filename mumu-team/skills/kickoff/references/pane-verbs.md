# Panes: herdr

Every command names its target pane.

| verb | command |
| --- | --- |
| `ready` | `$HERDR_PANE_ID` is set, and `herdr integration status` has no `claude: not installed` line; without both no session can be addressed or report its state. The fix is to run inside herdr, and `herdr integration install claude` |
| your address | `<your name>`, the bare name `herdr agent get` resolves; `<name>@<pane>` is `agent_not_found` |
| `live` | `herdr agent list`, whose JSON gives each agent's `pane_id`, `tab_id` and `agent_status` |
| `start` | `worker-start.py <checkout> <topic> <effort> <task-url> [--continue] [--leader <your address>] [--owner-effort]`: `<effort>` is `low` or `medium`, any other refused unless `--owner-effort` says the owner named it; starts the worker `<topic>-<n>-<k>` at the next attempt, or the newest with `--continue`, in its own worktree and tab, prompted kickoff's `work` with `--leader`, and prints `<name>@<pane> <worktree>` |
| `name` | this session's three names: `herdr tab rename <tab> <name>`, the tab being `herdr pane get $HERDR_PANE_ID`'s `tab_id`; `herdr agent rename $HERDR_PANE_ID <name>`; and `herdr agent prompt $HERDR_PANE_ID "/rename <name>"`, which applies when the turn ends |
| `prompt` | `herdr agent prompt <pane> "<text>"`; when it fails, retry it, else tell the owner. Success is printed before delivery, and a busy pane or an open dialog can swallow the text: read the pane before and after, resend when no turn carries it, and address by name, since a remembered pane id can be stale |
| `start-lead` | `lead-start.py <checkout> [<goal-url> \| --succeed <pane>] [-- <claude flags>]`, `<checkout>` the target checkout's root: opens a tab there and starts `<repo>-lead` as `--agent mumu-team:lead`, refusing when one is live, answers the folder-trust dialog, and prompts its kickoff; a start-up dialog in its tab is the owner's to answer there |
| `broadcast` | `prompt` each agent in `herdr agent list` whose name ends in `-lead`, but you, `see <url>`, as one `herdr agent prompt <literal-name> "see <url>"` Bash call per agent, no loop and no variable, so `Bash(herdr agent prompt *)` matches it |
| `close` | `worker-close.py <name>`: sends `/exit`, presses Enter on the background-work dialog when it shows (its option 2 would leave a session herdr does not list), and closes the tab once `live` no longer lists the agent |

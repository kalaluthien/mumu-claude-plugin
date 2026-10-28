# Message: herdr

herdr types a message into the receiver's pane and keeps no reply path, so the receiver replies by `comment` on the issue the message names.

| operation | how |
| --- | --- |
| `tell` | [tell-session.py](../../scripts/tell-session.py) `<name> <text-file>`, to a receiver that is not Claude Code, which waits until it is idle or done, sends, confirms it shows, and retries while it is blocked; `not delivered` and exit 1 say why, at once for a Claude Code receiver |
| `watch` | `herdr agent wait <name> --until idle --until done`, since a session that finished a turn is `done` |

- **Prompt**: `herdr agent prompt` exits 0 once the text is typed, not once read; a busy Claude Code session runs it after its turn, one at a tool prompt herdr recognises refuses it (`agent_blocked`, exit 1), and an unrecognised dialog reads `idle` and takes the text. `herdr agent read` of a blocked session fails `agent_not_idle`; read it with `--source visible`.

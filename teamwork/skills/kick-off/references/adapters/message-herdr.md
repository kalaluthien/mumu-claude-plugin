# Message: herdr

herdr types a message into the receiver's pane and keeps no reply path, so the receiver replies by `comment` on the issue the message names.

| operation | how |
| --- | --- |
| `tell` | [tell-session.py](../../scripts/tell-session.py) `<name> <text-file>`, which waits until the receiver is idle or done, sends, confirms it shows, and retries while it is blocked; `not delivered` and exit 1 say why |
| `watch` | `herdr agent wait <name> --until idle --until done`, since a session that finished a turn is `done` |

# Message herdr

herdr types a message into the receiver's pane and keeps no reply path, so the receiver replies by `comment` on the issue the message names.

| operation | how |
| --- | --- |
| `tell` | [tell-session.py](message-herdr/scripts/tell-session.py) `<name> <text-file>` |
| `watch` | `herdr agent wait <name> --until idle --until done`, since a session that finished a turn is `done` |

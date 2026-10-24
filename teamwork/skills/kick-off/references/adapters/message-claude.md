# Message: Claude Code

| operation | how |
| --- | --- |
| `tell` | `SendMessage` to the `ListAgents` name; to a cloud worker, its `cloud` row, from an interactive session. A cloud worker never `tell`s by `send_message` to a local session, which waits for the owner's trust card each session: it `comment`s its `BLOCKED:` or `REPORTED:` on its issue, which its manager watches |
| `ask` | `AskUserQuestion`, which a worker lacks |
| `notify` | `PushNotification` |
| `watch` | the heartbeat's idle line, which names each worker of your team once it waits; a cloud worker, by its `ListAgents` row, `idle`, and by its issue's comments |

- **Cloud, experimental, not for real work**: a cloud worker that ended its turn wakes on a `tell`, never on a comment.

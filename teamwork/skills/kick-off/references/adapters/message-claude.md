# Message Claude

A message reaches a Claude Code session, or the owner, through Claude Code's own tools.

| operation | how |
| --- | --- |
| `tell` | `SendMessage` to the session's name |
| `ask` | `AskUserQuestion` |
| `notify` | `PushNotification`, only while Remote Control is active in your session, since only it carries a push, which [print-remote-control.py](message-claude/scripts/print-remote-control.py) prints; else send no push, and keep the step in your tab |
| `watch` | the heartbeat's idle line, which names each worker of your team once it waits |

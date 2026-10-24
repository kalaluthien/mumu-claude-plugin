# Adapters

Which adapter does each port's operations of [protocol.md](protocol.md): the first row of a port whose condition holds.

| port | adapter | when |
| --- | --- | --- |
| board | [board-files.md](adapters/board-files.md) | `TEAMWORK_BOARD=files` |
| board | [board-github.md](adapters/board-github.md) | the project's repository is on GitHub |
| landing | [landing-github.md](adapters/landing-github.md) | the project's repository is on GitHub |
| message | [message-claude.md](adapters/message-claude.md) | the receiver is one `ListAgents` lists, or the owner |
| message | [message-herdr.md](adapters/message-herdr.md) | any other session herdr lists |
| session | [session-herdr.md](adapters/session-herdr.md) | the team runs in herdr |
| agent | [agent-claude.md](adapters/agent-claude.md) | you are a Claude Code session |

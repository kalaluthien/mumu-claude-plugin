# Adapters

Which adapter does each port's operations of [protocol.md](protocol.md): the first row of a port whose condition holds.

## Domain

| port | adapter | when |
| --- | --- | --- |
| board | [board.md](adapters/board.md) | always |
| landing | [landing-git.md](adapters/landing-git.md) | always |
| message | [message-claude.md](adapters/message-claude.md) | the receiver is a Claude Code session, every session teamwork starts, or the owner |
| message | [message-herdr.md](adapters/message-herdr.md) | a receiver of another kind herdr lists, such as Codex, never a Claude Code session |
| session | [session-herdr.md](adapters/session-herdr.md) | the team runs in herdr |
| agent | [agent-claude.md](adapters/agent-claude.md) | you are a Claude Code session |

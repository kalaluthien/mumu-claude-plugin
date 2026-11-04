# Adapters

Which adapter does each port's operations of [protocol.md](protocol.md): the adapters of the set your kick-off arguments name, else the first row of a port whose condition holds.

## Domain

| port | adapter | when |
| --- | --- | --- |
| board | [board.md](adapters/board.md) | always |
| landing | [landing-git.md](adapters/landing-git.md) | always |
| message | [message-claude.md](adapters/message-claude.md) | the receiver is a Claude Code session, every session teamwork starts, or the owner |
| message | [message-herdr.md](adapters/message-herdr.md) | a receiver of another kind herdr lists, such as Codex, never a Claude Code session |
| session | [session-cloud.md](adapters/session-cloud.md) | `CLAUDE_CODE_REMOTE` is `true`, a cloud session |
| session | [session-herdr.md](adapters/session-herdr.md) | the team runs in herdr |
| agent | [agent-claude.md](adapters/agent-claude.md) | you are a Claude Code session |

### Adapter sets

The manager picks each worker's set when it starts it and names it in the worker's kick-off arguments, `set <set>`; a worker with none uses `local`.

| set | board | landing | message | session | agent |
| --- | --- | --- | --- | --- | --- |
| local | [board.md](adapters/board.md) | [landing-git.md](adapters/landing-git.md) | [message-claude.md](adapters/message-claude.md); [message-herdr.md](adapters/message-herdr.md) only for a receiver of another kind | [session-herdr.md](adapters/session-herdr.md) | [agent-claude.md](adapters/agent-claude.md) |
| remote | [board.md](adapters/board.md) | none | [message-claude.md](adapters/message-claude.md), its cloud rows | [session-cloud.md](adapters/session-cloud.md) | [agent-claude.md](adapters/agent-claude.md) |

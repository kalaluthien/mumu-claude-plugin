# Adapters

Which adapter does each port's operations of [protocol.md](protocol.md): the adapters of the set your kick-off arguments name, else the first row of a port whose condition holds.

| port | adapter | when |
| --- | --- | --- |
| board | [board-files.md](adapters/board-files.md) | `TEAMWORK_BOARD=files` |
| board | [board-github.md](adapters/board-github.md) | the project's repository is on GitHub |
| landing | [landing-git.md](adapters/landing-git.md) | `TEAMWORK_LANDING=git` |
| landing | [landing-github.md](adapters/landing-github.md) | the project's repository is on GitHub |
| message | [message-claude.md](adapters/message-claude.md) | the receiver is a Claude Code session, every session teamwork starts, or the owner |
| message | [message-herdr.md](adapters/message-herdr.md) | a receiver of another kind herdr lists, such as Codex |
| session | [session-cloud.md](adapters/session-cloud.md) | `CLAUDE_CODE_REMOTE` is `true`, a cloud session |
| session | [session-herdr.md](adapters/session-herdr.md) | the team runs in herdr |
| agent | [agent-claude.md](adapters/agent-claude.md) | you are a Claude Code session |

## Adapter sets

The manager picks each worker's set when it starts it and names it in the worker's kick-off arguments, `set <set>`; a worker with none uses `local`.

| set | board | landing | message | session | agent |
| --- | --- | --- | --- | --- | --- |
| local | [board-github.md](adapters/board-github.md), or [board-files.md](adapters/board-files.md) by `TEAMWORK_BOARD` | [landing-github.md](adapters/landing-github.md), or [landing-git.md](adapters/landing-git.md) by `TEAMWORK_LANDING` | [message-claude.md](adapters/message-claude.md); [message-herdr.md](adapters/message-herdr.md) only for a receiver of another kind | [session-herdr.md](adapters/session-herdr.md) | [agent-claude.md](adapters/agent-claude.md) |
| remote | [board-github.md](adapters/board-github.md), its **Cloud** forms | [landing-github.md](adapters/landing-github.md), its **Cloud** forms | [message-claude.md](adapters/message-claude.md), its cloud rows | [session-cloud.md](adapters/session-cloud.md) | [agent-claude.md](adapters/agent-claude.md) |

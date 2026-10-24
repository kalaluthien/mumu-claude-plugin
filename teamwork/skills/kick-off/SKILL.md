---
name: kick-off
description: Use when a session is made its project's manager, by the owner or by another session, or is started as a worker by its manager. Not for the judge or another subagent, whose brief names the files it reads.
user-invocable: false
---

# Kick-off

Turn the owner's intent into merged work: one manager per project routes it, workers define and do it.

Arguments: $ARGUMENTS

## Route

`Read` [references/protocol.md](references/protocol.md), then the playbook of the first row that fits.

| arguments | role | playbook |
| --- | --- | --- |
| `worker <name> manager <manager>`, then a url or the owner's words | worker | [references/worker.md](references/worker.md) |
| `succeed <name>` | manager | [references/manager.md](references/manager.md)'s Succession |
| anything else | manager | [references/manager.md](references/manager.md) |

Do each operation they name as [references/adapters.md](references/adapters.md) says for the adapter in use.

**Write it right once**: a `gh` write passes its text by `--body-file <file>`, written first, never `--body` or `-b`, and carries a title of at most 40 characters, since a hook denies the call otherwise and nothing runs.

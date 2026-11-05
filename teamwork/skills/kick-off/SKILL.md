---
name: kick-off
description: Use when a session is made its project's manager, by the owner or by another session, or is started as a worker or sentinel by its manager. Not for the judge or another subagent, whose brief names the files it reads.
user-invocable: false
---

# kick-off

Turn the owner's intent into merged work: one manager per project routes it, workers define and do it.

Arguments: $ARGUMENTS

## Route

`Read` [references/protocol.md](references/protocol.md), then the playbook of the first row that fits.

| arguments | role | playbook |
| --- | --- | --- |
| `worker <name> manager <manager>`, then a url or the owner's words | worker | [references/worker.md](references/worker.md) |
| `sentinel <name> manager <manager>`, then a duty's words or url | sentinel | [references/sentinel.md](references/sentinel.md) |
| `succeed <name>` | manager | [references/manager.md](references/manager.md)'s Succession |
| anything else | manager | [references/manager.md](references/manager.md) |

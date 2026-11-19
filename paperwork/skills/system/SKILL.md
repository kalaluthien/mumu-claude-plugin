---
name: system
description: Use when a system, a process or requirements must be described so that a reader can rebuild it.
---

# system

Describe a subject, such as code, a process or requirements, as one checked contract a reader can rebuild it from.

## Domain

- **subject**: what is described; its **sources** are the code, documents, runs and people that can settle a question about it.
- **contract**: one JSON file holding the whole description: nodes, edges and areas, the levels that show them, scenarios, properties, terms and sources.
- **level**: one depth of the subject, small enough to read at once; a node **opens** the level that shows its inside.
- **tag**: the kind of a node, edge or area, which fixes the items worth recording of it; `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/scripts/check-contract.py tags` prints them.
- **reconstruction**: the measure of a contract: a reader who never saw the sources answers what a rebuild needs from the contract alone.

## Route

Take the cases in order; each playbook's steps go into the todo list.

| case | playbook |
| --- | --- |
| find what a reader needs to rebuild the subject | [references/extract.md](references/extract.md) |
| write or change the contract | [references/contract.md](references/contract.md) |
| word a text of the contract: a name, a purpose, a meaning, a note or a statement | [references/writing.md](references/writing.md) |
| show the contract to a person as a page | [references/page.md](references/page.md) |

## Rules

- **Contract only**: every view of the subject is made from the contract by code, so a change goes into the contract.
- **Seen, not supposed**: cite a source for each node and edge, and record what no source settles as a gap, never as a guess.
- **After a change to this folder**: run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/scripts/check-contract.py fixtures`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/fixtures/replay-read-aloud.py`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/fixtures/replay-gap-counts.py`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/relay/fixtures/replay-option-calls.py`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/fixtures/replay-malformed-contracts.py`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/fixtures/replay-contract-changes.py`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/fixtures/replay-prose-faults.py`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/fixtures/replay-reconstruction.py`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/fixtures/replay-edge-sorting.py` and `node ${CLAUDE_PLUGIN_ROOT}/skills/system/scripts/run-page.cjs sweep`, which draws every tag, item form and scenario of the fixtures the checker passes; each must print `PASS`.

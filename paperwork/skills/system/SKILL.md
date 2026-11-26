---
name: system
description: Use when a system, a process or requirements must be described so that a reader can rebuild it, or when the owner asks to apply a person's edits on a local HTML page to its file.
---

# system

Describe a subject, such as code, a process or requirements, as one checked contract a reader can rebuild it from.

## Domain

- **subject**: what is described; its **sources** are the code, documents, runs and people that can settle a question about it.
- **contract**: one JSON file holding the whole description: nodes, edges and areas, the levels that show them, scenarios, claims, terms and sources.
- **level**: one depth of the subject, small enough to read at once; a node **opens** the level that shows its inside.
- **tag**: the kind of a node, edge or area, which fixes the items worth recording of it; `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/scripts/check-contract.py tags` prints them.
- **reconstruction**: the measure of a contract: a reader who never saw the sources answers what a rebuild needs from the contract alone.

## Route

Take the cases that fit, in order; each playbook's steps go into the todo list.

| case | playbook |
| --- | --- |
| find what a reader needs to rebuild the subject | [references/extract.md](references/extract.md) |
| write or change the contract | [references/contract.md](references/contract.md) |
| word a text of the contract: a name, a purpose, a meaning, a note or a statement | [references/writing.md](references/writing.md) |
| show the contract to a person as a page | [references/page.md](references/page.md) |
| apply the changes a person makes on a local HTML page, such as comments, form values or diagram edits, to its file, only when the owner asks for it or hands those changes over (**Serve when asked**) | [references/relay.md](references/relay.md) |

## Rules

- **Contract only**: every view of the subject is made from the contract by code, so a change goes into the contract.
- **Seen, not supposed**: cite a source for each node and edge, and record what no source settles as a claim whose `fault` says so, never as a guess.
- **After a change to this folder**: run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/scripts/check-contract.py fixtures`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/fixtures/replay-read-aloud.py`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/fixtures/replay-gap-counts.py`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/fixtures/replay-option-calls.py`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/fixtures/replay-malformed-contracts.py`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/fixtures/replay-contract-changes.py`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/fixtures/replay-prose-faults.py`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/fixtures/replay-reconstruction.py`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/fixtures/replay-edge-sorting.py`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/fixtures/replay-check-page.py`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/system/fixtures/replay-serve-relay.py`, `node ${CLAUDE_PLUGIN_ROOT}/lib/fixtures/drive-page-colours.cjs`, `node ${CLAUDE_PLUGIN_ROOT}/lib/fixtures/drive-claim-badges.cjs`, `node ${CLAUDE_PLUGIN_ROOT}/skills/system/scripts/run-page.cjs sweep`, which draws every tag, item form and scenario of the fixtures the checker passes, and `node ${CLAUDE_PLUGIN_ROOT}/skills/system/scripts/run-relay.cjs`; each must print `PASS`. The two `node` runs drive a headless Chromium through `/private/tmp/relay-playwright/node_modules/playwright-core` (`npm install --prefix /private/tmp/relay-playwright playwright-core`, then `npx --prefix /private/tmp/relay-playwright playwright-core install chromium-headless-shell`) and print `FAIL` with the missing path where none is.

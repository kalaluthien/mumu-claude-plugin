---
name: flow
description: Use when interactions between systems, or a work plan, must be drawn as sequence diagrams a reader can build or run the work from. Not for a system's structure, which is the system skill's.
---

# flow

Describe how a subject unfolds in time, its calls between systems or its plan of work, as one checked contract a reader can build or run it from alone.

## Domain

- **flow contract**: one JSON file holding groups, levels, nodes, edges, tasks, fragments, milestones, properties, terms, sources and questions.
- **level**: one diagram, of kind `interaction` (systems across the top, time flowing down, the arrows between them) or `plan` (actors and resources down the left, time flowing right, the tasks on their lines); an edge **opens** a level that shows its inside, as UML `ref` does.
- **precedence**: what comes before what on a level; a **milestone** is one point in time, and the **critical path** of a plan is its longest chain of predecessors, counted in tasks.
- **tag**: the kind of a node, edge or task, which fixes the items worth recording of it; `python3 ${CLAUDE_PLUGIN_ROOT}/skills/flow/scripts/check-contract.py tags` prints them.

## Route

| case | playbook |
| --- | --- |
| write or change a flow contract | [references/contract.md](references/contract.md) |
| show a contract to a person as a page | [references/page.md](references/page.md) |
| find what a reader needs, or word a text | `${CLAUDE_PLUGIN_ROOT}/skills/system/references/extract.md` and `${CLAUDE_PLUGIN_ROOT}/skills/system/references/writing.md`, read for nodes, edges and tasks |

## Rules

- **Written contracts only**: take the subject from written sources, such as a specification, a runbook or a plan, and cite one for each record; record what no source settles as a gap.
- **After a change to this folder**: run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/flow/scripts/check-contract.py fixtures`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/flow/fixtures/replay-critical-path.py`, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/flow/fixtures/replay-deep-contract.py` and `node ${CLAUDE_PLUGIN_ROOT}/skills/flow/scripts/run-page.cjs`; each must print `PASS`.

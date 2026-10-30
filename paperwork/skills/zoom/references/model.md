# Model

Turn an existing system (code, docs, configs, screens, a process), or requirements for one not yet built (a PRD, a spec, an intent), into one checked Schema document, each claim carrying the line it rests on, and name its defects.

## Domain

Write the document in the grammar, [schema/assets/schema.json](schema/assets/schema.json), as [schema/authoring.md](schema/authoring.md) says, and draw each level by what it claims:

- [Topology](schema/semantics.md#topology) for what exists and what depends on what; for a design, the things it keeps and how they relate;
- [Statechart](schema/semantics.md#statechart) for the lifetime of one subject (status, mode, phase) and for a run that hands work on; for a design, each kept thing's whole life, from what creates it to what ends it;
- [Opening a level](schema/semantics.md#opening-a-level) for a node whose inside the reader needs.

### Faults

Name each defect of a state level by Mirdin and Koppel's four abstraction-mapping faults:

- **Missing**: a situation of the system that no state or event handles;
- **Illegal**: a state or call the document allows that the system must never reach;
- **Redundant**: two states that react to every event alike;
- **Overloaded**: one state that means two things the system tells apart.

## Steps

1. Write the document from the root level down, one entry at a time, as the Order rule says.
2. Run `schema/scripts/check-schema.py check doc.json` after each entry, until it prints `ok`.
3. Run `schema/scripts/check-schema.py check doc.json --root <repo>`, which resolves each `path:line` under the repository, until it prints `ok`.
4. Hand over the document's path, the commit, the last two outputs, and either the defects or the open decisions with their recommended options and the rules to prove.

## Rules

- **Order**: follow the system's own run: start where something enters it (a command, a request, a timer, a person's goal), follow it through what handles it to what it hands out, then take the next entry. Read each source once, when the run first reaches it, and write every part it supports:
  - entry point: a Scenario starting there;
  - step: its node, the edge it hands on, the Scenario's next step;
  - branch, failure, loop: the edge, and a Scenario for the branch;
  - thing and fields: a part with its attributes and calls;
  - lifetime: a state level of its subject, its transitions;
  - check, guard, invariant: a rule there.
- **Designed run**: from requirements, decide each thing once, when the run first needs it. An open decision goes in the hand-over with your recommended option, which the document takes.
- **One step per edge**: one edge or event is one indivisible step in the source, since a proof treats it as one. Split a step the source takes in parts (a read then a write, a check then an act) into one edge each. Write a sync only where the source makes both events happen in one atomic action, such as a lock, a transaction or one call.
- **As it is**: model an existing system with its defects. Name each one in the hand-over: a fault above, or a rule the system breaks.
- **No gaps**: a design leaves no fault; each transition says whom it refuses, and when.
- **Source**: give each node, edge and rule `meta.source` as `path:line` or `path:line-line` relative to the repository root, the line that shows it, or for a requirement the line that asks for it. A url stands only for a system known solely from web documents.
- **Description**: give each `meta.description` what a reader needs, including the source's reason where the label does not show it.
- **Rule per requirement**: state each requirement that must always hold as a `must` rule with its guard, so the prove playbook can check it.
- **Commit**: name the commit you read in the hand-over, so every pointer resolves later.

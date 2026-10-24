# Interpret

Turn an existing system (code, docs, configs, screens, a process) into one checked Schema document, each claim carrying the line it rests on, and name its defects.

## Domain

Write the document in the grammar, [schema/assets/schema.json](schema/assets/schema.json), as [schema/authoring.md](schema/authoring.md) says, and pick each level's kind by what it claims:

- [Topology](schema/semantics.md#topology) for what exists and what depends on what;
- [Workflow](schema/semantics.md#workflow) for a run that hands work on;
- [State](schema/semantics.md#state) for the lifetime of one subject (status, mode, phase);
- [Opening a level](schema/semantics.md#opening-a-level) for a node whose inside the reader needs.

## Defects

Model the system as it is, defects included. Name each one in the hand-over: a situation nothing handles (Missing), a reachable impossible state or call (Illegal), two states that react alike (Redundant), one state meaning two things (Overloaded), or a rule the system breaks.

## Steps

Command paths are relative to this file.

1. Write the document from the root level down, one entry at a time, as the Order rule says.
2. Run `schema/scripts/check-schema.py check doc.json` after each entry, until it prints `ok`.
3. Run `../scripts/resolve-pointers.py evidence doc.json --root <repo> --sha <commit>`; fix each unresolved pointer. `../fixtures/pointers-to-nothing.json` makes `evidence`, `constraints` and `faults` each report one unresolved pointer; run it after changing the script.
4. Hand over the document's path, the commit, the last two outputs and the defects.

## Rules

- **Order**: follow the system's own run: start where something enters it (a command, a request, a timer, a person's goal), follow it through what handles it to what it hands out, then take the next entry. Read each source once, when the run first reaches it, and write every part it supports:
  - entry point: a trigger and a Scenario starting there;
  - step: its node, the edge it hands on, the Scenario's next step;
  - branch, failure, loop: the edge with its mark, and a Scenario for the branch;
  - thing and fields: a component with its attributes and relations;
  - lifetime: a state level of its subject, its events;
  - function, call: an operation; check, guard, invariant: a rule there;
  - number, limit, timeout: a quantity.
- **One step per edge**: one edge or event is one indivisible step in the source, since a proof treats it as one. Split a step the source takes in parts (a read then a write, a check then an act) into one edge each. Write a sync only where the source makes both events happen in one atomic action, such as a lock, a transaction or one call.
- **Evidence**: give each node and edge you read from a source `meta.evidence` as `path:line` or `path:line-line` relative to the repository root, the line that shows it. A url or a sha cannot be read back, so use them only when no line exists.
- **Explanation**: where the source's reason is not obvious from the label, add `meta.note` saying why, in plain words, never opening with `<Word>:`, which marks a fault.
- **Commit**: write the commit you read as the document's own top-level `meta.evidence`, `["<sha>"]`, and in the hand-over, so every pointer resolves later and [recheck.md](recheck.md) finds what changed since.

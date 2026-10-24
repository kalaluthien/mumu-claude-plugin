# Requirements

Turn requirements for a system not yet built (a PRD, a spec, an intent) into one checked, buildable Schema document,
each part tied to the requirement it serves.

## Domain

Write the document in the grammar, [../schema/assets/schema.json](../schema/assets/schema.json), as
[../schema/authoring.md](../schema/authoring.md) says; each kind claims what its reading says:

- [Topology](../schema/semantics.md#topology): the things the system keeps and how they relate;
- [Workflow](../schema/semantics.md#workflow): who does what, in what order, with what handed on;
- [State](../schema/semantics.md#state): each kept thing's whole life, from what creates it to what ends it.

## Rules

- **Order**: follow the designed system's run: start where something enters it (a goal, a request, a timer), decide what handles
  it up to what it hands out, then take the next. Decide each thing once, when the run first needs it. An open decision
  goes in the hand-over with your recommended option, which the document takes.
- **Constraint**: give each node, edge and rule that a requirement asks for `meta.constraint` as
  `<path or url>#<requirement>`, the requirement's name or id as its source writes it, such as a bold rule name.
- **Rule per requirement**: state each requirement that must always hold as a `must` rule with its mechanism (a
  guard, a pre- or postcondition), so the prove playbook can check it.
- **No gaps**: leave no Missing, Illegal, Redundant or Overloaded state; each operation says whom it refuses, and when.

## Steps

Command paths are relative to this file.

1. Write the document per the Order rule, one entry at a time, running `../schema/scripts/check-schema.py check doc.json` after each, until it prints `ok`.
2. Run `scripts/resolve-pointers.py constraints doc.json --root <repo> --sha <commit>` when the
   requirements live in a repository; fix each untraced one.
3. Hand over the document, the open decisions with their recommended options, and the rules to prove.

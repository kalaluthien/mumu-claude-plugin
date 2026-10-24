# Improve

Turn a checked Schema document into an improved one by stated criteria, keeping every behaviour it states, and name each fault it fixes.

## Domain

The original and the improvement are both written in the grammar, [schema/assets/schema.json](schema/assets/schema.json), as [schema/authoring.md](schema/authoring.md) says. A state level's faults are read by [its semantics](schema/semantics.md#state), and a workflow's by [its semantics](schema/semantics.md#workflow).

## Faults

Name each fault by Mirdin and Koppel's four abstraction-mapping faults, read on a state level:

- **Missing**: a situation of the system that no state or event handles;
- **Illegal**: a state or call the document allows that the system must never reach;
- **Redundant**: two states that react to every event alike;
- **Overloaded**: one state that means two things the system tells apart.

Write each one on the element it concerns as `meta.note` `<Fault>: <what is wrong and what changed>`, with `meta.evidence` pointing at the source line that shows it, and mark the change with `meta.diff`.

## Criteria

Unless the ask states its own, compare by these counts, which `compare-models.py` prints:

- economy (elements), duplication, one term per entity: fewer;
- deep modules: more; low coupling and cycles: fewer;
- near-decomposability: at most 7 nodes on a level;
- requisite variety, essential state, operations that both return and change: fewer;
- the four faults above: fewer.

## Steps

Command paths are relative to this file.

1. Run `../scripts/compare-models.py original.json original.json`; pick the counts or faults where it does worst, or the ask's own criteria.
2. Copy the original to the improved document, restructure for those criteria, and write each fault as Faults says.
3. Rerun `compare-models.py original.json improved.json` until it exits 0; run `../scripts/resolve-pointers.py faults improved.json --root <repo> --sha <commit>` when the evidence lives in a repository.
4. Hand over the improved document, the counts table beside the original, and each fault with its evidence.

## Rules

- **Kept behaviour**: every original Scenario and rule stays, by slug and meaning. Adding behaviour is free; a removal fails the comparison until the user approves. `../scripts/compare-models.py original.json improved.json` prints `kept` or `dropped` per slug, `changed` where a kept slug's text differs, each count below on both documents, then the improved document's check; exit 0 means nothing dropped and the check passes.

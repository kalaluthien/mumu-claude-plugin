# Improve a system

Turn a checked `system.json` (the original; analyse it first if there is
none) into 2 or 3 improved models, each keeping every behaviour of the
original.

**Kept behaviour.** Every original Scenario and rule stays, by slug and by
what it does. A new behaviour is an addition; a removed one is a removal
awaiting the user's approval, and fails the comparison until approved.

**Counts.** `${CLAUDE_PLUGIN_ROOT}/skills/drill-it/scripts/compare-models.py original.json improved.json` prints
`kept` or `dropped` per slug, each count below on both models, and the
improved model's check; it exits 0 only when nothing is dropped and the check
passes.

| count | improves when |
| --- | --- |
| economy: nodes + edges + rules + operations | fewer |
| duplication: texts and formulas stated twice | fewer, or a kept copy named |
| one term per entity: names on two things | fewer |
| deep modules: inner nodes / (1 + crossing edges) per opened node | more |
| low coupling: edges across partitions / all edges; cycles | fewer |
| near-decomposability: most nodes on a level; nesting depth | at most 7; not deeper |
| requisite variety: triggers and states nothing handles | fewer |
| essential state: elements no Scenario uses | fewer |
| data/calculation/action: operations that both return and change | fewer (software and process models; say why it is skipped for others) |
| four states: Missing, Illegal, Redundant, Overloaded | fewer, from the `four-states` check and your reading |

**Options.** Counts conflict: economy against deep modules, requisite
variety, near-decomposability and four states; duplication against low
coupling; deep modules against data/calculation/action; essential state
against requisite variety. Each option takes one side of one such pair as far
as the kept behaviour allows, and holds or improves every other count.

## Steps

1. Run `compare-models.py original.json original.json` for the original's
   counts, and pick the 2 or 3 pairs where the original does worst.
2. For each option, copy the original to `improved-<n>.json` and change its
   structure for its side of the pair; run `compare-models.py` after each
   change, until it exits 0.
3. Recommend one option, first.

## Hand-back

Under the purpose's section, per option, recommended first: its path, the
pair it takes a side of, the additions and removals (`none` when none), and
the counts table `compare-models.py` printed, original beside it.

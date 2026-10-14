# Improve a system

Turn the original checked `system.json` into 2 or 3 improved models; build them all, never asking which.

**Kept behaviour.** Every original Scenario and rule stays, by slug and meaning. Adding behaviour is free; a removal fails the comparison until the user approves.

**Counts.** `${CLAUDE_PLUGIN_ROOT}/skills/drill-it/scripts/compare-models.py original.json improved.json` prints
`kept` or `dropped` per slug, `changed` where a kept slug's text differs, each count below on both models, and the improved check; exit 0 means nothing dropped, check passes.

- economy: nodes+edges+rules+operations; fewer
- duplication: texts and formulas stated twice; fewer, or name a kept copy
- one term per entity: names for two things; fewer
- deep modules: inner nodes/(1+crossing edges) per opened node; more
- low coupling: edges across partitions/all edges; cycles; fewer
- near-decomposability: most nodes on a level, at most 7; nesting depth, not deeper
- requisite variety: triggers and states nothing handles; fewer
- essential state: elements no Scenario uses; fewer
- data/calculation/action: operations that return and change; fewer (software, processes; else say why)
- four states: Missing, Illegal, Redundant, Overloaded; fewer (`four-states` check, your reading)

**Options.** Conflicts: economy against deep modules, requisite variety,
near-decomposability and four states; duplication against low coupling; deep
modules against data/calculation/action; essential state against requisite
variety. Each option takes one side of one pair as far as kept behaviour
allows, holding or improving the rest.

## Steps

1. Run `compare-models.py original.json original.json` (no Alloy); pick 2 or 3 pairs where it does worst.
2. Per option, copy the original to `improved-<n>/system.json`, restructure for its
   side, rerun `compare-models.py` until exit 0, then run `check-system.py check improved-<n>/system.json --prove` once.

## Hand-back

Under the purpose's section, per option, recommended first: path, pair,
additions and removals (`none` if none), and the `compare-models.py` counts
table beside the original.

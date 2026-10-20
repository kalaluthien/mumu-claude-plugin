# Rewrites

Every criterion `measure-judge.py alpha rubric-first.json runs-first` sent to rewrite, then those a later round sent. Rounds 1 to 3 graded the five `answers/` three times; with five answers one dissenting verdict drops alpha to about 0, so rounds 4 and 5 graded 30 answers three times, as `judge-prompt.md` says. The final alphas are `measure-judge.py alpha rubric.json runs`, round 5; "undefined" means all 90 verdicts agreed.

## no-silent-drop

- Alpha before: 0.000 (round 1, 5 answers)
- Alpha after: undefined, every verdict the same

Old: Every original Scenario and rule has a counterpart with the same slug and behaviour in each improved model, or the hand-back names it as removed and awaiting approval.

New: Every `slug` in the original model's `scenarios` and `rules` appears as a `slug` in the same array of each improved model, or the hand-back names it as removed.

## metric-counts-match

- Alpha before: 0.222 (round 1, 5 answers)
- Alpha after: 1.000

Old: Every other count or ratio the hand-back states (repeated texts, two-name things, inner nodes over crossing edges, crossing share, cycles, nodes per level, depth, unhandled triggers, unused elements, mixed elements) equals the recount from the model files.

New: Every value the hand-back states for the original or an improved model for cycles, most nodes on a level, nesting depth, or operations that return and change equals the recount from that model file.

## counts-all-per-option

- Alpha before: 0.000 (round 1, 5 answers)
- Alpha after: 0.950

Old: For the original and every option, the hand-back gives a value for each count criterion (size, repeated texts, one term per entity, deep modules, coupling, near-decomposability, unhandled triggers, unused elements, mixed elements, four states).

New: For the original and every option, the hand-back gives a value under each of these ten names or the synonym in brackets: economy (size), duplication (repeated texts), one term per entity, deep modules, low coupling (coupling), near-decomposability (most nodes on a level), requisite variety (unhandled triggers), essential state (unused elements), data/calculation/action (mixed elements), four states.

## option-has-conflict

- Alpha before: 0.682 (round 1, 5 answers)
- Alpha after: undefined, every verdict the same

Old: Each extra option names a pair of criteria from the report's Conflicts that move in opposite directions, or the hand-back gives one answer and says that one model wins or ties every count.

New: Every improved model file after the first that the hand-back offers comes with two named criteria it trades, one better and one worse than in the original or the first option, as a `Pair:` line does; a hand-back that names one improved model file or none meets it.

## counts-hold

- Alpha before: 0.000 (round 1, 5 answers)
- Alpha after: 1.000

Old: In the recommended model every recounted count of size, repeated texts, one term per entity, deep modules, coupling, near-decomposability, unhandled triggers, unused elements and mixed elements is better than or equal to the original's, or the hand-back states the conflicting criterion that excuses it.

New: For the recommended option, every count in the hand-back's own table that is worse than the original's is excused by a criterion the hand-back names for that option as better in exchange, as a `Pair:` line does; a hand-back with no count table fails.

## levels-within-seven

- Alpha before: 0.000 (round 1, 5 answers)
- Alpha after: undefined, every verdict the same

Old: Every level of the recommended model holds 7 nodes or fewer and its nesting depth is not deeper than the original's, or the hand-back states the reason.

New: Counting the `nodes` array of `level` and of every node's `opens`, no level of the recommended model holds more than 7 nodes and its longest `opens` chain is no longer than the original's, or the hand-back states the reason.

## recommended-first

- Alpha before: 0.462 (round 1, 5 answers)
- Alpha after: 0.840

Old: Exactly one option is recommended and it is listed first; a single answer stated as the answer meets it.

New: The hand-back marks exactly one option or proposal as recommended, and no other option comes before it.

## change-lists-match

- Alpha before: round 1 1.000 (5 answers), round 4 0.386 (30 answers)
- Alpha after: 1.000

Old: The hand-back's lists of added and of removed Scenarios, rules and behaviours equal the differences between the original and each improved model, with 'none' written for an empty list.

New: Every `slug` of `scenarios`, `rules` or `operations` that an improved model has and the original lacks is named as added, every one the original has and the improved model lacks is named as removed, and the hand-back names nothing as added or removed that the files do not show.

## size-counts-match

- Alpha before: round 2 0.364 (5 answers)
- Alpha after: 0.916

Old: Every nodes, edges, rules and operations count, and every sum of them, that the hand-back states for the original or an improved model equals the recount from that model file.

New: Every economy value, and every nodes, edges, rules or operations count, that the hand-back states for the original or an improved model equals the recount from that model file.

## fewer-bad-states

- Alpha before: round 3 0.000 (5 answers)
- Alpha after: 1.000

Old: The hand-back states that the recommended model has no more Missing, Illegal, Redundant or Overloaded states than the original, and fewer or none.

New: For the original and the recommended model, the hand-back states a count of Missing, Illegal, Redundant and Overloaded states, or that there are none, and the recommended count is 0 or below the original's.
## Not measured

no-silent-drop, option-has-conflict and levels-within-seven got 1 in all 90 round-5 verdicts: every hand-back in the sample meets them, so alpha cannot tell agreement from chance there. An answer that breaks one, such as a dropped slug, a second option with no `Pair:` line or a level of eight nodes, would measure them.

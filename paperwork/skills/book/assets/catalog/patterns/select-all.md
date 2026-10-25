# select-all: the reader judges each candidate on its own against a rule, with no count given
family: problem
elements: stem, items, exhibit
differs: each item is judged yes or no against one rule with no bin structure and no count given, so a near-pass must be refused item by item. sort-bins cannot force this: it files into bins

## Why it works
Each item is a separate pass or fail against one rule, so the reader cannot reach the answer by eliminating the odd one out. It prevents single-choice cards that a guess of 33% can pass (card-kind).
The list mixes clear passes, clear failures and at least one near-miss; the why names the exact condition that holds or fails.

## Parts
- stem: the rule, once; no count of correct items.
- items: 4 to 6 items with `ok` flags and a `why` for the wrong flags; a near-miss item is allowed.
- exhibit: attached when the rule reads a shown thing.

## Examples
Source book: the UX book (ids are its card ids or unit and line).
- task-compose-valid (u-compose): six model requests; select the ones a validator rejects before drawing. Essential content: wrong type, missing required slot and unknown name fail; a missing optional slot passes.
- task-prim-select (u-primitive): a photo grid in selection mode with four numbered parts; tick the ones that are commands. Essential content: the checked photo (fills the object) and the delete button act; the count text and the filter chip only report or filter.
- task-str-select (u-structure): six readings of a 2D map of 2,000 embedded items; select those the map supports. Essential content: similarity inside a cluster and a mixed-label cluster as a mislabel lead hold; cluster width, gaps between clusters and density do not.
Elsewhere: Which of six sentences in a contract clause are enforceable under the rule just given?

## Compose and vary
- Combines with: near-miss (one candidate is one condition short), spot-defect.
- Vary: the rule's domain and the candidate forms (code, claims, parts); keep the number correct between 2 and half.
- Usual failure: all correct items share a surface feature (length, position), or none is a near-miss.

## Seed
Does any correct item differ from the incorrect ones by something other than the rule?

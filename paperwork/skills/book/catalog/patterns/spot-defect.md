# spot-defect: the reader locates the flaw on a shown artefact instead of reciting the rule it breaks
family: problem
elements: stem, exhibit, marks, answer, rival

## Why it works
Numbered marks turn a diagnosis into a pointing act: the reader must see the fault where it sits, and each wrong mark is a part that looks suspicious for a reason. It prevents the card that names the fault in the stem (card-exhibit, card-claim).
Rivals are parts that really are salient or wrong-looking but sit outside the rule, so the idea, not intuition, separates them (card-rival, card-unique).

## Parts
- stem: describes the symptom people report, not the cause, and says which kind of part to find.
- exhibit: the full artefact, drawn once, with every fact the why will cite visible in it.
- marks: one numbered mark per candidate (`target`, `note`); options cite `mark`, and the set of marks equals the set of options (parts-match).
- answer / rival: the why opens on what is true of that part, then says why it does or does not cause the symptom.

## Examples
Source book: the UX book (ids are its card or figure ids, with the unit in parentheses).
- ask-per-spot (u-percept): a settings page with three marked parts; find the one that makes a row read as belonging to the wrong group. Essential content: a heading with less space above than below attaches to the group before it.
- ask-per-promo (u-percept): a transfer confirmation with numbered parts; find the one that pulls the eye ahead of the facts to confirm. Essential content: a promotion banner breaks the hierarchy.
- ask-human-select (u-human): a selection-mode mock screen with three marks; users tap a row to open it and only change selection. Essential content: unselected rows look the same as normal rows, so the mode change is unseen.
Elsewhere: An invoice with three numbered lines; one is a tax rate applied to the wrong base. Same move: find the line, not the rule.
# Compose and vary
- Combines with: near-miss (one marked part meets all but one condition), read-exhibit.
- Vary: the domain supplies the artefact (page, log, form, contract); keep three marks, each one a plausible culprit. Make two marks look worse than the true one.
- Usual failure: the true defect is the only unusual part, so the reader finds it by oddity alone (card-rival); or a mark has no note the why can use.

## Seed
Cover the stem: is the defect findable only by applying the idea, with at least one decoy that looks worse?

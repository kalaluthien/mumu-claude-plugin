# annotated-exhibit: a drawn artefact with numbered marks the prose and cards can point to
family: visual
elements: exhibit, marks, alt

## Why it works
The marks let the text name a part by number and let a card ask about it (card-exhibit). It prevents paragraphs that describe positions on an artefact the reader cannot see.
Each mark has a `target` and a `note`; the prose before the figure asks, the marks locate, and the caption says what is shown (fig-show-say).

## Parts
- exhibit: a drawn artefact whose facts are all visible (facts-shown).
- marks: `{n, target, note}`, numbered in reading order; a card citing them shares the set (parts-match).
- alt: the artefact, the number of marks, what the marks refer to.

## Examples
Source book: the UX book (ids are its card or figure ids, with the unit in parentheses).
- fig-chat-turn (u-chat): a conversation screen with seven numbered parts (context chips, a user turn, turn actions, a streaming answer, stop, follow-up chips, input). Essential content: the numbers name every part the unit then discusses.
- fig-chat-turn-after (u-chat): the same screen after the unit's changes, with numbered ask-back, edit and stop controls. Essential content: marks map to the unit's design decisions.
- fig-views-brushing (u-views): a scatter brush, the highlighted list rows and a distribution bar, numbered 1, 2, 3. Essential content: one selection drives all three views, and the numbers are the order the text walks through.
Elsewhere: A bank statement with numbered lines, one per fee type, used by the paragraph that explains each.
# Compose and vary
- Combines with: spot-defect (marks become options), mock-screen, structure.
- Vary: choose the artefact the unit works on repeatedly; number in reading order.
- Usual failure: marks that cover more than one part, or marks the prose never cites.

## Seed
Does every mark point at one part, and is every mark used in the prose or a card?

# scenario-decide: the reader chooses a move for a stated situation, with numbers that rule rivals out
family: problem
elements: setup, stem, answer, rival

## Why it works
A decision card states a situation and asks what to do. It prevents advice-by-slogan: the numbers in the setup are what make the right move right, and each rival is right in a different situation (card-unique, card-rival).
Difficulty sits on the idea, not on arithmetic (card-flat).

## Parts
- setup: every number and name the decision rests on; kept short.
- stem: the decision and who decides.
- answer / rival: each option is an action; `right_when` names the situation where it would win, and `ruled_out_by` points to a setup fact that excludes it here.

## Examples
Source book: the UX book (ids are its card or figure ids, with the unit in parentheses).
- ask-cycle-where (u-cycle): a tag edit is saved; where should the saved acknowledgement appear? Essential content: where the user's eyes already are.
- ask-per-help (u-percept): a help line must read as belonging to a password field; which gap to change? Essential content: shorten the input-to-help gap to 4 px against 12 px.
- ask-cycle-map (u-cycle): four burner knobs placed without labels; which layout needs no memorising? Essential content: layout copies the burners' layout.
Elsewhere: A shop has two registers and a queue of ten; which rule saves the most time?
# Compose and vary
- Combines with: compare-designs, estimate.
- Vary: the situation and the constraint; make each rival the best move in a nearby situation.
- Usual failure: all options are acceptable, so the decision is taste.

## Seed
For each rival, which fact in the setup rules it out in this case?

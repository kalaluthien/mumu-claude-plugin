# intervene: the reader changes one part and predicts what moves, in the right layer
family: problem
elements: setup, change, answer, rival

## Why it works
The card holds the case fixed, changes one thing and asks for the consequence, so the reader must reason about a mechanism, not recall a fact. It prevents "improves / worsens" answers that need no model (card-intervene).
Options are layered consequences: the first-order effect, a second-order effect, and the condition under which the change flips. The reader who stops at the first layer picks a rival.

## Parts
- setup: every number and name the consequence depends on, stated once (`facts[]`).
- change: `base`, exactly one `change`; the stem says "everything else stays".
- answer / rival: each option carries a `layer`; the right one is the layer that holds after the change and names the new cost or duty it creates.

## Examples
Source book: the UX book (ids are its card or figure ids, with the unit in parentheses).
- ask-cycle-intervene (u-cycle): a transfer button gets an immediate "sending" state while the server still takes 3 s. Essential content: repeat presses stop, but the app now owes the user a rollback when the send fails.
- ask-idm-axes (u-idiom): six small panels on a shared axis switch to per-panel automatic ranges. Essential content: every curve fills its panel, so a small rise and a large one look alike.
- ask-per-region (u-percept): six dots seen as three pairs get a faint rectangle around two of them with distances unchanged; what grouping is seen first? Essential content: the enclosed pair wins over proximity (a frame variant: the exhibit is the current frame, the change is the delta).
Elsewhere: A clinic moves appointment reminders from 24 h to 2 h before; the first-order effect is fewer no-shows, the second is more last-minute cancellations.
# Compose and vary
- Combines with: setup-heavy compute (numbers), frames (the exhibit is the current frame), near-miss (change that stops one condition short).
- Frame variant: the exhibit is the current frame of a scene with fixed geometry, the stem names one change and asks for the next state, and each rival moves a wrong object or a second one. Use it only when the unit has a frames figure to extend; the usual failure is a next frame that changes two objects, so two rivals are defensible.
- Vary: change a different kind of thing (order, boundary, assumption, input) and keep the asked layer visible in the options.
- Usual failure: the change touches two parts, or the options are three sizes of the same effect rather than three layers (card-intervene).

## Seed
Is exactly one thing changed, and do the options differ by layer rather than by magnitude?

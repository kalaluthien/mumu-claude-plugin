# demo: a small tool the reader operates to see one variable change one measure
family: visual
elements: demo, axes, alt

## Why it works
The reader changes exactly one control and watches one measure move, so the idea is a measurement and not a claim (fig-data). It prevents statements about effects that the reader can only believe.
A demo changes exactly the variable it claims to show; everything else is fixed in the script.

## Parts
- demo: a book.js widget `name`, its `controls`, the `measures` it prints and the `question` it answers.
- axes: when a plot is drawn, with units.
- alt: static fallback that names the control, the measure and the result.

## Examples
Source book: the UX book (ids are its card or figure ids, with the unit in parentheses).
- fig-enc-demo (u-encoding): a table's fields reassigned to x, y, colour and size, with the spec shown beside it. Essential content: a type that does not fit the channel is refused with a reason.
- fig-respond-easing (u-respond): an easing curve, its velocity curve and a ball moved by the same curve. Essential content: the curve shape sets how the move feels.
- fig-chat-lab (u-chat): a lab with streaming and chips toggles for a conversation. Essential content: the reader turns each feature on and off and sees the cost.
Elsewhere: A loan calculator where only the interest rate moves and the monthly total is read off.
# Compose and vary
- Combines with: estimate and compose (the task is done in the demo), computed-plot.
- Vary: choose one control and one measure; print the number so the reader can quote it.
- Usual failure: two controls move together, or the result can only be seen by a viewer who already knows it.

## Seed
Does the demo change one thing only, and does it print the measure?

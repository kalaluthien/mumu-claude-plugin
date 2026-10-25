# estimate: the reader produces a number from stated inputs, with feedback that names the error
family: problem
elements: stem, given

## Why it works
A mental estimate or an input from a slider tests whether the reader can use the model quantitatively. It prevents verbal agreement without being able to use the quantity (card-flat: mental numbers).
Feedback is directional: a too-low and a too-high answer each get a hint naming what was missed, and the final why shows the arithmetic.

## Parts
- stem: the quantity to find and the unit of the answer.
- given: `given{name: value, unit}` listing every number the estimate needs; `ans`, `tol`, `lo`, `hi` for the accepted range and the hints, and the why that shows the steps.

## Examples
Source book: the UX book (ids are its card ids or unit and line).
- task-cycle-est (u-cycle): the average number of rows opened to find one diverged run among six. Essential content: (1+2+3+4+5+6)/6 = 3.5.
- task-human-klm (u-human): sum the operator times for a click, a hand move and two keys: 1.35 + 1.1 + 0.2 + 0.4 + 0.2 + 0.2 = 3.45 s.
- task-per-dark (u-percept): find the darkest grey that keeps 4.5:1 on a dark background with a demo slider. Essential content: grey value 137 (4.52:1), 136 fails.
Elsewhere: Estimate the break-even number of uses for a tool that costs 12 s to learn and saves 3 s each time.

## Compose and vary
- Combines with: computed-plot (the figure shows the curve), demo.
- Vary: the quantity and the model; give all inputs and keep the arithmetic small (card-flat).
- Usual failure: the tolerance admits two readings, or a hint gives the answer away.

## Seed
Is every input given in the card, and does each wrong-direction hint name the missed step?

# worked-sum: a quantity is added up frame by frame so the total is read off, not asserted
family: visual
elements: scene, steps, alt
differs: each frame adds one term and shows the running total, and the last frame states the sum. frames shows a process changing shape; computed-plot draws a curve; neither lets the reader check an addition term by term
Numbers come from the book's own model (`facts[]`); a frame's figures must match the text.

## Why it works
A total in prose looks arbitrary. Drawn one term per frame with the running figure, the reader can follow the arithmetic and see which term dominates. It prevents a figure whose number the reader must take on trust (fig-data).

## Parts
- scene: the quantity's parts as objects, each with a fixed place across frames.
- steps: one term added per frame, with the running total on the frame.
- alt: names the quantity, the terms and the total.

## Examples
Source book: the UX book (ids are its card or figure ids, with the unit in parentheses).
- fig-human-klm (u-human, computed): one task cut into operators frame by frame with times. Essential content: M 1.35 s, P 1.1 s, K 0.2 s add to the total compared with the second design.
- fig-human-fitts-bits (u-human, computed): distance fixed and width halved per frame, with the difficulty in bits under each. Essential content: each halving adds one bit.
- fig-rec-capture-cost (u-record): cumulative time of two ways of recording after each added question. Essential content: the extra cost to write is overtaken by the cost to find as questions accumulate.
Elsewhere: A monthly budget built one expense per frame, the remaining balance shown after each.

## Compose and vary
- Combines with: computed-plot (the totals become a curve), estimate (a card asks for the same sum).
- Vary: sum, product or difference; keep one term per frame.
- Usual failure: two terms enter in one frame, or the last frame's total differs from the text.

## Seed
Can the reader recompute the total from the frames alone?

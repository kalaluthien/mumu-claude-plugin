# flow: a path of steps from a start to an outcome, with the place where it can break
family: visual
elements: graph, steps, alt

## Why it works
The path is drawn in order and the reader sees where it can stop, loop or hand over (fig-draw-path). It prevents a sequence of four or more steps that exists only in a paragraph.
The break point is part of the drawing: a step that can fail has its two outcomes drawn.

## Parts
- graph: ordered `nodes` and `edges`; `point` marks the step or hand-off that matters.
- steps: optional frames that light the path one segment at a time.
- alt: start, end, the break.

## Examples
Source book: the UX book (ids are its card or figure ids, with the unit in parentheses).
- fig-compose-retry (u-compose): an agent sends a three-element spec, the validator returns a failure with the path, the agent fixes that one element, and after two failed retries the flow falls back to plain text. Essential content: the error goes back to the model, with a limit.
- fig-trust-loop (u-trust): a statement's mark returns through three loops (this answer, evaluation cases, confidence calibration). Essential content: the last loop moves the line between words and cards.
- fig-spec-typing (u-speculate): four typed characters at 300 ms and a start before Enter. Essential content: work started early overlaps the wait.
Elsewhere: An order from checkout to delivery with the payment check drawn as a two-way step.
# Compose and vary
- Combines with: structure, state, frames.
- Vary: choose the path the reader would follow in their work; mark the one place where it can leave the path.
- Usual failure: all steps look alike, so the decision point is not visible.

## Seed
Is every branch drawn, and is the break point the one the prose names?

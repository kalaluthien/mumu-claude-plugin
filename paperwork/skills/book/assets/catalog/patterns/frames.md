# frames: a process is redrawn on the same geometry so the reader sees one change per scene
family: visual
elements: scene, steps, alt

## Why it works
The case's own objects are drawn again for each step with one change between neighbours, so the reader follows the mechanism instead of a summary (fig-frames, fig-draw-path). It prevents a process of four or more parts that is only narrated.
The prose before asks the question, the frames show it, and the caption states what changed, never what the reader should conclude (fig-show-say, fig-no-answer).

## Parts
- scene: objects with ids and fixed geometry; nothing moves unless a step says so.
- steps: `[{delta, state, note}]`; `delta` names the one object or declared group that changes; `read` says what to see at the end.
- alt: names the kind (frames), what the sequence encodes and the point (fig-alt).

## Examples
Source book: the UX book (ids are its card or figure ids, with the unit in parentheses).
- fig-cycle-gulf (u-cycle): goal and screen at first apart; each frame adds one path or breaks it. Essential content: the execution path, the evaluation path, then the two gaps where they break.
- fig-nav-stacks (u-navigate): two stacks, one per tab, drawn after each press. Essential content: each stack grows, is kept when the tab changes, and shrinks on back.
- fig-prim-four-cell (u-primitive): a decision tree redrawn per event, one branch lit each time. Essential content: the first question sends the case to execution, the next to its cell.
Elsewhere: A water cycle in four frames: the same lake, cloud and field; one arrow added per frame.
# Compose and vary
- Combines with: intervene (a card asks for the next frame, see its frame variant), state, flow, computed-plot (a quantity under the scene).
- Vary: choose the one thing that changes (a state, an object, a value) and keep the rest identical; declare a group if several objects move together.
- Usual failure: frames redraw the scene differently, so the reader compares layouts instead of states (one-change).

## Seed
Between any two frames, is exactly one thing different, and is it the thing the caption names?

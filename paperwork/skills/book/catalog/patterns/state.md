# state: the states of one thing and the events that move it between them
family: visual
elements: graph, scene, alt

## Why it works
A state diagram shows what can happen next from each state, so the reader sees the missing transition. It prevents behaviour explained as a list of cases.
Each edge carries an `event`; every state is drawn as the thing itself, not a box with a label only (fig-draw-path).

## Parts
- graph: nodes are states; edges `{from, to, event}`; `point` marks the state or edge in question.
- scene: optional small drawing of the thing in each state.
- alt: lists the states and the transition the figure is about.

## Examples
Source book: the UX book (ids are its card or figure ids, with the unit in parentheses).
- fig-chat-scroll-states (u-chat): the two scroll states while a reply streams, and the user actions that move between them. Essential content: follow-at-bottom pauses when the user scrolls up and shows a "new content" cue; reaching the bottom or pressing the cue resumes it.
- fig-human-mode (u-human): the same key pressed with a mode light off and on. Essential content: one input, two outcomes, decided by a state the light shows.
- fig-respond-archive (u-respond): a row after an archive tap that removes it at once. Essential content: removal without a question, with undo as the only way back.
Elsewhere: A parcel: ordered, packed, shipped, delivered, with "returned" reachable only from shipped.
# Compose and vary
- Combines with: frames (one frame per state), flow, mock-screen.
- Vary: choose what counts as a state (what the person can do next) and add the event labels; show the impossible transition when it is the lesson.
- Usual failure: two events with one label, or a state no event can leave.

## Seed
Can every state be left, and does each edge carry the event that causes it?

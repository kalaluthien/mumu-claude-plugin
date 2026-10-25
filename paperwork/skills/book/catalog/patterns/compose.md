# compose: the reader builds a small artefact that a rule can check, rather than choosing one
family: problem
elements: stem, model, answer

## Why it works
The reader acts on an interactive artefact (type a command, finish a task, adjust a value) and the page checks the result against `checks[]`. It prevents cards that only recognise the right thing when shown it (card-kind: input matches the manipulation).
Each check is a property of the result, so many correct builds pass and the card never prescribes one.

## Parts
- stem: the goal and a limit (length, count, time) that makes the idea necessary.
- model: `brief`, `model` of the artefact and `checks[]` the result must meet.
- answer: the recorded outcome with a why that explains why the checks pass.

## Examples
Source book: the UX book (ids are its card ids or unit and line).
- task-cmd-pal (u-command): in a palette, run "stop experiment" with at most three typed characters. Essential content: the reader finds the shortcut that fuzzy search allows.
- task-wf-agent (u-workflow): open the detail of a stalled plan and approve the stop, finishing the plan. Essential content: the path through a supervised agent flow.
- task-per-contrast (u-percept): make secondary text as pale as allowed while keeping 4.5:1. Essential content: the boundary value is the answer.
Elsewhere: Write a one-sentence reminder that includes who, what and a time under 80 characters; a validator checks the three parts.

## Compose and vary
- Combines with: estimate (a numeric build), demo.
- Vary: the artefact and the check; keep checks mechanical, not stylistic.
- Usual failure: the checks admit an answer that violates the idea, or exactly one build passes, which turns it into a quiz.

## Seed
Does a build that breaks the idea fail a check, and does at least one other correct build pass?

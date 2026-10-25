# order: the reader reconstructs a sequence whose order is the idea
family: problem
elements: stem, items

## Why it works
The reader places steps, layers or priorities in their order, so the model's ordering is tested, not just its names. It prevents learning the parts of a process without how they depend on each other (card-kind: drag what moves).
The why for each item says why that slot, not the next: what the step needs from the one before.

## Parts
- stem: names the ordering principle (cause to effect, coarse to fine, most to least important).
- items: a `sequence` of 4 to 7 items with `why` per slot; distractor-free, because every wrong order is a wrong dependency.

## Examples
Source book: the UX book (ids are its card ids or unit and line).
- task-cycle-order (u-cycle): seven actions of a person setting a room temperature, put in the cycle's order. Essential content: goal, plan, specify, act, perceive, interpret, compare.
- task-docs-order (u-docs): four sentences of a message that gives a recommendation first. Essential content: request, strongest evidence, costs, method.
- task-prim-order (u-primitive): five parts of a delivery app ordered from smallest to largest composition level.
Elsewhere: Order the five steps of a recipe so each uses what the last produced.

## Compose and vary
- Combines with: sort-bins (sort, then order within a bin), explain-why.
- Vary: the principle (time, size, priority); a new case, not the unit's worked sequence (card-new-case).
- Usual failure: the order is the order of mention in the text, or two adjacent slots could swap.

## Seed
Could any two adjacent items swap without breaking the stated principle?

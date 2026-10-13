# Option cards

The reader must choose among options: approaches, designs, layouts, tools, plans. The page lays them side by side, on one set of criteria, so the reader can point at one.

## Form

- **Criteria first**: 3 to 5 criteria the choice turns on, fixed before any option is written; they appear once, as the criteria table's rows, never also as a list.
- **Cards**: one `.cards` `<article>` per option: a short label, its one-sentence argument and its main risk; numbers stay in the table.
- **Criteria table**: one table in a `.scroll` box, a row per criterion and a column per option, cost as a number (files, lines, ms, money) among the rows, so the reader compares one criterion across options in one line; it follows the cards. A row with no checked value in any column is cut.
- **Shown, not described**: an option the reader judges by eye (a layout, a style, a screen) is drawn inside its card as a small live mock in HTML and CSS, every card at the same scale and with the same content; never a description of how it would look.
- **Pick**: the recommended card has `class="pick"`; under the cards, one sentence says why, and the fact that would change it.
- **Reply**: a button per card with `data-reply="I choose <label>: <its key trade-off>"`, which the base page writes into `.reply`, so the reader pastes back one line.

## Steps

1. Count the options: the ones the ask names, and a third only where a real one exists; offer at least three for an open "show me options", since two is a yes-or-no in disguise.
2. **One-sentence test**: write each option's argument in one sentence; one sentence that fits two options means one idea restyled, so replace one.
3. Settle each criterion's value per option from the code, the docs or a measurement; mark one you could not check "not verified".
4. Build from the base page with `.answer` (the recommendation in one sentence), `.cards`, the criteria table, the pick sentence, `.reply` and `.next`; the card marked `pick`, the answer and the pick sentence name the same option.

## Gotchas

| symptom | fix |
| --- | --- |
| cards differ in length and order | the same parts in each, the same order; what only one card has goes in the criteria table or is cut |
| options look alike | the one-sentence test failed: redesign one |
| a mock overflows on a phone | the cards stack under 30rem; keep a mock under 15rem wide or scale it with `transform` inside an `overflow: hidden` box |

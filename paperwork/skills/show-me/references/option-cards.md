# Option cards

## Form

- **Criteria**: 3 to 5 criteria the choice turns on, as the rows of one table, a column per option, cost as a number (files, lines, ms, money) among them; numbers stay in the table, which follows the cards.
- **Cards**: one `.cards` `<article>` per option, each with the same parts in the same order: a short label, its one-sentence argument and its risk.
- **Shown, not described**: an option the reader judges by eye (a layout, a style, a screen) is drawn inside its card as a small live mock in HTML and CSS, every card at the same scale and with the same content, showing every item the text names.
- **Pick**: the picked card has `class="pick"`; under the cards, one sentence says why, and the fact that would change it; `.answer` names the pick.
- **Reply**: a button per card with `data-reply="I choose <label>, accepting <its risk>"`.
- **Next**: the choice the reader makes.

## Steps

1. Fix the criteria before writing any option.
2. Count the options: the ones the ask names, and a third only where a real one exists; at least three for an open "show me options".
3. **One-sentence test**: write each option's argument in one sentence; one sentence that fits two options means one idea restyled, so replace one.
4. Settle each criterion's value per option.

## Gotchas

| symptom | fix |
| --- | --- |
| a mock overflows its card on a phone | give it `width: 100%` of the card, or scale it with `transform` inside an `overflow: hidden` box |

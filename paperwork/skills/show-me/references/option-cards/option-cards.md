# Option cards

The reader chooses among named alternatives: approaches, designs, layouts, tools, or a verdict such as approve or ask for changes. Placed last when parts before it set out the situation.

## Parts

Write the part's body as a fragment; `assemble-page.py` wraps it and adds this folder's CSS. The page's plan carries `"reply"` (empty is fine), so the pick buttons have a box to fill.

| part | use | holds |
| --- | --- | --- |
| Lead | required | one `<p>`: the pick, why, and the fact that would change it |
| Cards | required | `.cards`, one `<article>` per option, each with the same parts in the same order: a short label, its one-sentence argument, its risk, and a button with `data-reply="I choose <label>, accepting <its risk>"`; the picked card has `class="pick"` |
| Mock | optional | inside each card, for an option the reader judges by eye (a layout, a style, a screen): a small live mock in HTML and CSS, every card at the same scale and with the same content, showing every item the text names |
| Criteria | optional | under the cards, one table in `.scroll` of the 3 to 5 criteria the choice turns on, a column per option, cost as a number (files, lines, ms, money) among them; numbers stay in this table |

## Gotchas

| symptom | fix |
| --- | --- |
| a mock overflows its card on a phone | give it `width: 100%` of the card, or scale it with `transform` inside an `overflow: hidden` box |

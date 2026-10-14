# Option cards

The reader chooses among named alternatives or a verdict such as approve or ask for changes. Placed last.

## Parts

Write a fragment; `assemble-page.py` wraps it and adds this folder's CSS. The page's plan carries `"reply"` (empty is fine) for the pick buttons.

- **Lead** (required): one `<p>`: the pick, why, and the fact that would change it
- **Cards** (required): `.cards`, one `<article>` per option, same parts in order: label, one-sentence argument, risk, and a button `data-reply="I choose <label>, accepting <its risk>"`; the picked card has `class="pick"`
- **Mock**: in each card, for an option judged by eye: a small live HTML and CSS mock, same scale and content on every card, showing every item the text names
- **Criteria**: under the cards, one table in `.scroll`: 3 to 5 criteria, a column per option, cost as a number among them; numbers stay here

## Gotchas

| symptom | fix |
| --- | --- |
| a mock overflows its card on a phone | `width: 100%`, or `transform` scale in an `overflow: hidden` box |

# Option cards

## Parts

- **Criteria**: 3 to 5 criteria the choice turns on, as the rows of one table, a column per option, cost as a number (files, lines, ms, money) among them; numbers stay in the table, which follows the cards.
- **Cards**: one `.cards` `<article>` per option, each with the same parts in the same order: a short label, its one-sentence argument and its risk.
- **Shown, not described**: an option the reader judges by eye (a layout, a style, a screen) is drawn inside its card as a small live mock in HTML and CSS, every card at the same scale and with the same content, showing every item the text names.
- **Pick**: the picked card has `class="pick"`; under the cards, one sentence says why, and the fact that would change it; `.answer` names the pick.
- **Reply**: a button per card with `data-reply="I choose <label>, accepting <its risk>"`.
- **Next**: the choice the reader makes.

## CSS

```css
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); gap: 1rem; margin: 1rem 0; }
.cards > article { border: 1px solid var(--ink); padding: 1rem; display: flex; flex-direction: column; gap: .5rem; }
.cards > article.pick { border: 3px solid var(--accent); }
.cards h3 { margin: 0; }
```

## Gotchas

| symptom | fix |
| --- | --- |
| a mock overflows its card on a phone | give it `width: 100%` of the card, or scale it with `transform` inside an `overflow: hidden` box |

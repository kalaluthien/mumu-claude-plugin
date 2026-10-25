# mock-screen: a static picture of an interface (UI-specific: in another field draw that field's own artefact), as the reader would see it
family: visual
elements: exhibit, kit-tree, alt

## Why it works
The exhibit is built from the book's drawn kit so it looks like the thing and is the same from page to page (fig-home). It prevents descriptions of screens and screenshots with unreadable detail.
It is looked at, never operated; interaction belongs to a demo.

## Parts
- exhibit: rendered from a `kit-tree` of kit components and props; text in it is the text the reader needs.
- kit-tree: only components in the kit; a part that does not exist is added to the kit once.
- alt: names the screen kind, what it shows and the point.

## Examples
Source book: the UX book (ids are its card or figure ids, with the unit in parentheses).
- fig-rec-three-windows (u-record): three windows of one incident (a channel stream, a tracker entry with named fields, a report that opens with the conclusion). Essential content: the same event, three shapes.
- fig-rec-thread-panel (u-record): a busy support channel where replies are indented under the message and shown in the stream. Essential content: the design under test, drawn so the reader can predict its effect.
- fig-present-postures (u-present): the same list as a table, big cards, a single row. Essential content: one set of data at three widths of display.
Elsewhere: A settings page for a thermostat drawn once and reused in each section about it.
# Compose and vary
- Combines with: small-multiples, annotated-exhibit, before-after, option-exhibit in compare-designs.
- Vary: choose the device form and the content that the card or paragraph turns on; keep fake names readable.
- Usual failure: decorative detail the question does not need, or text too small to read.

## Seed
Is every fact the card or paragraph uses readable in the picture?

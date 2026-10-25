# before-after: two versions of the same thing with one change, side by side
family: visual
elements: pair, alt

## Why it works
The reader sees what a single change did to the same thing, so the effect is attributed to the change (fig-frames: one change). It prevents comparisons in which the layout also changed.
The caption states the change; what the reader should see goes in the prose (fig-show-say).

## Parts
- pair: `before`, `after` drawn on identical geometry; exactly one `change` declared.
- alt: names the pair, the change and the point.

## Examples
Source book: the UX book (ids are its card or figure ids, with the unit in parentheses).
- fig-col-restructure (u-collection): a wiki tree before (four nested folders) and after (one type level plus facets). Essential content: year, quarter and team move from folders to facets on the report.
- fig-human-edge-menu (u-human): the same cursor path against a menu inside the window and a menu at the screen edge. Essential content: the edge stops the cursor on the target.
- fig-docs-gulf (u-docs): the same action cycle drawn for an app and for a document. Essential content: in a document the execution line is thin and the evaluation line thick.
Elsewhere: A form before and after moving the error message next to the field.
# Compose and vary
- Combines with: frames, small-multiples, compare-designs (as option exhibits).
- Vary: choose a change that cannot be confounded with another (one property, one position).
- Usual failure: the "after" also fixes a second thing, so the effect has two causes.

## Seed
If you list everything that differs between the two, is the list one item long?

# isotype: counted marks or cells, one drawn item per unit, so the reader counts instead of reading a number
family: visual
elements: series, panels, alt

## Why it works
Items drawn one by one let the reader count and compare by quantity without a scale (fig-channel). It prevents a ratio stated as a percentage that a reader cannot picture.
One mark means one unit and the key says how many it stands for; the cells are the cases, not decoration.

## Parts
- series: items with a `value` and the mark that one unit gets.
- panels: cells or groups, with the same mark and scale across the panels.
- alt: the unit, the groups and the point.

## Examples
Source book: the UX book (ids are its card or figure ids, with the unit in parentheses).
- fig-compose-nine-cells (u-compose): nine cells for when a screen appears and who owns its layout, one example case in each. Essential content: the cells are filled with representative cases from the unit.
- fig-col-four-cells (u-collection): two 2x2 grids, one for this book's way of splitting actions and one for a documentation scheme. Essential content: two criteria with two values each make the four cells.
- fig-per-variables (u-percept): visual variables against four kinds of reading, with a filled mark where a variable supports a reading. Essential content: only position and size support quantitative reading.
Elsewhere: Ten people drawn per cell, three shaded: a reader sees "3 in 10" directly.
# Compose and vary
- Combines with: structure, small-multiples, computed-plot (counted outcomes in place of an interval).
- Vary: one unit per mark; choose groups with a shared key and the same unit.
- Usual failure: marks of different sizes or a cell with a different scale, so counts cannot be compared.

## Seed
Does one mark stand for the same amount in every cell?

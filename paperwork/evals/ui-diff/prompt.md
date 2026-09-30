---
max_turns: 24
timeout_seconds: 600
allowed_tools: [Skill, Read, Write, Bash]
runs: 3
---

Our chat view opens a long conversation scrolled to the bottom. Before a row is shown it reserves an estimated height, measures the real one while the row stays hidden, then reveals it. We changed the estimate for a strip of 9 searched images:

- before: every row type has a constant estimate; the image strip gets 96 px.
- after: the estimate is width-aware. At a 650 px column the tiles sit 4 to a line, (650 - 3·12) / 4 = 153.5 px wide and so 115 px tall; the 9th tile is capped at 220 px tall; the strip is 115 + 12 + 115 + 12 + 220 = 474 px, and the footer adds 32, so 506 px.
- measuring (`ResizeObserver → admitMeasuredPartSample → commit`): the left side goes 96 → 474, grows 378 px, scrolls to the bottom again and 5 rows leave the window before the reveal; the right side reads 474 → 474, within the 1 px drift tolerance, so nothing moves.
- the rows above the strip: user 48, trace 80, prose 80. Totals: before 1,788 px with 11 rows mounted; after 2,166 px with 6 rows mounted.

Show how the two versions behave, step by step, as a page saved to `cold-open.html` in the current directory.

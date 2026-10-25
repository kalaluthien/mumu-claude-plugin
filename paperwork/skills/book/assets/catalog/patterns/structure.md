# structure: a structure of four or more parts is drawn with its links, so the reader sees what contains or depends on what
family: visual
elements: graph, alt
differs: four or more parts with typed links (contains, depends on, points to), so the reader traces a path or a parent. fork cannot force this: it has one question and two ends

## Why it works
The parts and their relations are shown as boxes and links the reader can trace (fig-draw-path). It prevents a hierarchy, a record layout or a dependency described only in a paragraph.
One kind of link per diagram; the reader's question (what hangs from what?) names the layout.

## Parts
- graph: `nodes` (each with a label from the prose) and `edges` (typed); `point` names the node or edge the figure is about.
- alt: names the structure kind, what the links mean and the point.

## Examples
Source book: the UX book (ids are its card or figure ids, with the unit in parentheses).
- fig-rec-block-tree (u-record): a block with its fields and a page that holds child blocks. Essential content: links form a mesh, but each block has exactly one parent.
- fig-nav-focus-tree (u-navigate, computed): a repository tree with focus on one file. Essential content: ancestors score -3, siblings -5, farther branches fold at -7.
- fig-rec-links (u-record): an incident pointing at a thread, a report, a run and a decision, and the decision replacing an older one. Essential content: references run in one direction, so a replaced decision stays reachable.
Elsewhere: An org chart where each person has exactly one manager, with the span of control labelled.
# Compose and vary
- Combines with: annotated-exhibit, flow, isotype.
- Vary: choose which relation is drawn (contains, calls, owns); fold what the question does not need.
- Usual failure: edges of two meanings in one style, or a node with a label the prose does not use.

## Seed
Does each edge mean one thing, and does every label appear in the prose?

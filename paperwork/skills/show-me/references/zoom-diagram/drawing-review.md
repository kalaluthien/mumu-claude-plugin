# Drawing review

## Principles

- One thing to watch at a time: only the selection is inverted.
- Every mark has a job, with one signal per meaning.
- Nothing needs explaining: no title, figure number, hint or display switch.
- Calm: one eased movement per navigation, and none under reduced motion.
- Type has roles: names on the drawing in handwriting, identifiers and
  formulas in mono, sentences in sans, kinds and field labels in small caps.

## What a right drawing shows

- **Marks.** Each mark matches the model field that sets it
  ([model-writing.md](../../../drill-it/references/model-writing.md), Paths and partitions); a wrong mark
  is a wrong field.
- **Edges.** Orthogonal; no label touches a node, another label or another
  edge, and edges from different sources never share a stretch of line.
  Quantities sit in mono beside their element.
- **Syncs** are written on their events (`push (→ receive)`), not drawn.
- **Note.** A rule row wears its standing and opens to its sentence, its
  formula, then its counterexample. With nothing selected the note shows the
  level's media.
- **Walk.** A Scenario or a counterexample shows one step at a time. The
  step's node is selected, what came before is heavier, what comes later is
  plain, and anything outside the walk fades. The time bar has one tick per
  step and nothing plays by itself; a tap outside the walk ends it.

## Critic's pass

After `make-diagram.py make` passes, look at every level at both widths and in
both themes (`render out.html --shots DIR` saves them). Check that arrow tips
sit on borders, nothing is clipped, every opening node has a chevron, every
node a screen shows (a part, a state, an activity) shows that screen, and the
Principles hold. A wide level below the root scrolls sideways in full screen
on a phone, and that is not clipping.

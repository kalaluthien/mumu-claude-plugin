# Drawing review

## Principles

- One thing to watch at a time: only the selection is inverted.
- Every mark has a job and comes from the model, with one signal per meaning.
  The one warning ink is used only for failure.
- Nothing needs explaining: no title, figure number, hint or display switch.
- Calm: one eased movement per navigation, and none under reduced motion.
- Type has roles: names on the drawing in handwriting, identifiers and
  formulas in mono, sentences in sans, kinds and field labels in small caps.

## What a right drawing shows

- **Nodes and marks.** A corner radius tells the level kind (components 4,
  activities 11, states pills); the initial state has a dot, an abstract
  component is dotted, an opening node has a chevron. The main path is
  heavier, a failure path is in the warning ink, an optional element is
  dashed, and an `unsure` one gets "?". The legend lists only marks in use.
- **Edges.** Orthogonal; no label touches a node, another label or another
  edge, and edges from different sources never share a stretch of line.
  Quantities sit in mono beside their element.
- **Syncs** are written on their events (`push (→ receive)`), not drawn.
- **Note.** A rule row wears its standing and opens to its sentence, its
  formula, then its counterexample. With nothing selected the note shows the
  level's media, never a panel on how the page was drawn.
- **Walk.** A Scenario or a counterexample shows one step at a time. The
  step's node is selected, what came before is heavier, what comes later is
  plain, and anything outside the walk fades. The time bar has one tick per
  step and nothing plays by itself; a tap outside the walk ends it.

## Critic's pass

After `make-diagram.py make` passes, look at every level at both widths and in
both themes (`render out.html --shots DIR` saves them). Check that arrow tips
sit on borders, nothing is clipped, every opening node has a chevron, every
node a screen shows (a part, a state, an activity) shows that screen, only the selection is
inverted, and nothing would need explaining to a newcomer. On a
phone a wide level scrolls sideways in full screen; that is not clipping.

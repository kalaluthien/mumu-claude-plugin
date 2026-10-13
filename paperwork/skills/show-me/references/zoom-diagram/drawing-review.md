# Drawing review

## Principles

- One thing to watch at a time: only the selection is inverted.
- Every mark has a job and comes from the model, with one signal per meaning.
  The one warning ink is used only for failure.
- Nothing needs explaining: no title, figure number, hint or display switch.
- Calm: one eased movement per navigation, and none under reduced motion.
- Type has roles: names on the drawing in handwriting, identifiers and
  formulas in mono, sentences in sans, kinds and field labels in small caps.

## Drawing

- **Ink.** Black ink on paper, like a whiteboard sketch: borders drawn once
  round with a small overshoot, edges with a slight wobble and a two-stroke
  arrowhead. The sketch is seeded by element id, so a model always draws the
  same sketch.
- **Nodes.** Corner radius tells the level kind: components 4, activities 11,
  states pills. The initial state has a dot, an abstract component is dotted,
  and a node that opens a level has a chevron.
- **Edges.** Orthogonal: straight between neighbours, otherwise an L,
  otherwise a Z; two edges between one pair run as a lane pair. No label
  touches a node, another label or another edge, and edges from different
  sources never share a stretch of line.
- **Marks.** The main path is heavier, a failure path is in the warning ink,
  an optional element is dashed, and an unconfirmed one gets "?". A legend
  lists only the marks, abstract components and triggers the level uses.
- **Quantities.** A node's stock, count or capacity sits on its bottom left
  corner in a dotted box (`n=350`, `≤ 40 beds`); an edge's flow, count or
  deadline follows its label (`118 GtC/yr`, `within 21 d`), in mono.
- **Syncs** are written on their events, not drawn: `push (→ receive)` on the
  `when` event and `receive (← push)` on the `then` event.
- **Partitions** and regions are dotted boundaries with their names; a small
  square port marks where an edge crosses one.
- **From outside.** A trigger enters from an open circle, with clock hands
  when it repeats. A parent's artifact enters or leaves through a square port;
  tapping it goes up to that artifact.

## Card

Top to bottom: a breadcrumb of the levels above (tapping one goes up) ending
in the current level's name; a full-screen button; the level's `why`; the time
bar while a run plays; the drawing; and the note.

- **Level menu.** The current level's name opens the Levels tree on the left
  and the level's Scenarios as cards to its right, swiped sideways; on a
  phone the cards sit under the tree in a bottom sheet. On a wide screen it
  opens in place and stands in for the board.
- **Wide screens.** The note is pinned beside the selection, the drawing's
  column only as wide as the drawing, and a long note scrolls inside, at most
  a screen tall.
- **Narrow screens.** The drawing keeps its text at 9 px or more and scrolls
  sideways past the width under the edge fade, and the note is a bottom sheet
  with the same round close button as full screen.

## Note

- **Header.** A meta line holds the kind in small caps, a mark's legend
  sample, the partition as a dotted chip and, on an artifact that is a
  component, a link to it. The name follows in handwriting; an edge adds its
  route `from → to`, with partition chips only where it crosses one.
- **Body.** The description, source chips and media. Media heads read
  `KIND e.g. Title`. Verbatim text (code, payload, tree, diff, screen) sits in
  an ink box; sentences (example, quote, facts, pitfall, insight) on a ruled
  margin, warning ink for a pitfall and heavier for an insight. An insight
  reads: move, VS the usual design, → the gain, then the rule.
- **Groups.** A component lists its Attributes as `name: Type`, then
  Operations and Rules; an edge has Operations, Guard and Syncs. An operation
  row opens to its explanation, pre, post and modifies. A rule row wears its
  standing (guard, assumed, ideal, holds, or a dashed "can break") and opens
  to its sentence, then its formula laid out over lines (body under its
  quantifier, keywords in the mid ink), then the run that breaks it.
- **Nothing selected.** The level's media, and no panel on the plan: the
  reader asked for the system, not for how it was drawn. A node left closed
  by the plan says so in its note.
- **Plan.** `show` can hide formulas, replays or media.

## Runs

A run is something that happens over time, shown one step at a time: a
Scenario walks its steps, and a rule Alloy can break replays the run that
breaks it. Choosing one starts it at its first step and replaces any
selection.

- **Selected and highlighted.** The step highlights what it reaches and the
  edges it arrives by (heaviest ink). One of them is selected (inverted, with
  the note beside it): the node the step is at, until the reader picks
  another highlighted node or edge.
- **Time bar.** Under the legend: the run's name, earlier and later buttons,
  a rail with one tick per step, and `3 / 9`. Drag the rail, tap a tick, or
  use the arrow keys to go to any step, back as well as forward. Nothing plays
  by itself.
- **Drawing.** What came before is heavier, what comes later is plain, and
  anything outside the run fades. Each node of the run has its step numbers on
  its top right corner.
- **Taps.** A highlighted node or edge is selected; another node of the run
  takes the run to that node's next step; an edge never moves the run;
  anything outside the run ends it and is selected as usual.
- **Forks and joins.** Branches side by side share a step, and its tick stacks
  one dot per branch. An edge to a later join stays highlighted until the
  join, and the join lists every way in.
- **Levels.** A step on another level goes there with the usual movement;
  going to a level the run visits keeps the run.
- **Note.** The run's name; the step's `does` and `expects`; the highlighted
  things as chips to select; then the selection: how it was reached
  (`from → artifact`), its sentence, and only the operations and rules the run
  uses there.

## Critic's pass

After `make-diagram.py render` passes, look at every level at both widths and in
both themes (`render out.html --shots DIR` saves them). Check that arrow tips
sit on borders, nothing is clipped, every opening node has a chevron, every
node a screen shows (a part, a state, an activity) shows that screen, only the selection is
inverted, and nothing would need explaining to a newcomer. On a
phone a wide level scrolls sideways in full screen; that is not clipping.

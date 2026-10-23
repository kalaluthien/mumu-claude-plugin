# Semantics

What a Schema document means, kind by kind. The grammar, [assets/schema.json](assets/schema.json), says what may be
written; this file says what it claims, so a renderer draws it and a prover checks it the same way.

A document is a tree of levels from its root `level`; a node opens the level inside it. Each level has one kind, and
time means something different in each.

## Topology

A topology level is a typed graph: each node is a component, an instance of the type its label names, and each edge
a relation, a field from the source's type to the target's, read from source to target. Time plays no part, so a
rule on a node or edge is an invariant that holds in every instance of the graph. It answers "what is there, and what
depends on what".

## Workflow

A workflow level is a Petri-net-like flow: each activity is a transition that fires once the artifacts on its edges in
are present, and each edge is a place that holds the artifact handed on, its `must` rules acting as guards. A fork
puts a token on every branch and a join fires only when all have arrived; a trigger puts a token in from outside, and
a port is a place shared with the parent level. State lives only while a run goes; partitions say who does each
activity.

## State

A state level is a Harel statechart over one subject: each node is a state, the set of subject instances in it, and
each edge an event that moves an instance from one state to the next. Each region is orthogonal and holds every
instance in exactly one of its states, from its `initial` state on; regions change on their own and meet only
through syncs, where an event in one region, while a state holds, causes an event in another.

## Opening a level

A node that opens a level of another kind shows a different view of the same thing (`link: view`): a component's
workflow, an activity's states. A node that opens a level of its own kind refines it: the child's ports carry exactly
the parent node's edges, so what holds of the parent holds of the child; `link: nest` drops that claim. A state level
opened from a state of its own subject needs no ports: an event into the parent enters the child at its initial state, and an event out
of the parent leaves whichever child state holds, as in a Harel superstate: an instance is in a child state exactly
while it is in the parent, and the child's events happen only there. A child level with `history` is entered instead
where it was last left, as SCXML's [history](https://www.w3.org/TR/scxml/#history) state: shallow history resumes the
child state each region last held, its own inside entered afresh; deep history resumes every level below as well. The
first entry, with nothing to resume, takes the initial state. A child level of another subject only zooms in: its
states are not linked to the parent's. A trigger into a child state fires only inside the parent, since entering the
parent takes the initial state.

## Metadata

`meta` annotates any document, level, node or edge without changing what it claims: reserved keys record a remark, a
change, the evidence it rests on and the requirement it serves, and any other key carries a value of the format its
name ends in.

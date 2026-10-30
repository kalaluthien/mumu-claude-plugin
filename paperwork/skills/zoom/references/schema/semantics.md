# Semantics

What a Schema document means. The grammar, [assets/schema.json](assets/schema.json), says what may be written; this file says what it claims, so the page draws it and Alloy checks it the same way.

A document is a tree of levels from its root `level`; a node opens the level inside it. A level is a topology, a statechart, or both, told apart by each edge's `kind`.

## Topology

An edge of `kind: call` is a relation: a field from the source's type to the target's, read from source to target, on nodes that are parts of the system. Time plays no part, so a rule on a part or a call is an invariant that holds in every instance. It answers "what is there, and what depends on what".

## Statechart

An edge of `kind: transition` is an event that moves one instance of the level's `subject` from one state to the next, and a node it touches is a state, the set of instances in it. Each region is orthogonal and holds every instance in exactly one of its states, from its `initial` state on. Regions change on their own and meet only through syncs, where an event in one region, while a state holds, causes an event in another in the same step.

## Opening a level

An edge that crosses a level's boundary is written on the outer level, ending on the opener, so every edge joins two nodes of one level.

A state level opened from a state of its own subject makes that state a Harel superstate: an instance is in a child state exactly while it is in the parent, an event into the parent enters the child at its initial state, an event out of the parent leaves whichever child state holds, and the child's events happen only there. Every other opened level only zooms in, and its nodes are not linked to the parent's.

## Areas

An area groups the nodes of one level that a reader takes in as one. It exists only because it is cohesive, by more links inside than outside, or because people use its name, its `unit`, such as a team or a deploy unit.

## Metadata

`meta` says where an element comes from and what a reader needs to know about it, without changing what it claims.

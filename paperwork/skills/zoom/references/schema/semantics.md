# Semantics

What a Schema document means, kind by kind. The grammar, [assets/schema.json](assets/schema.json), says what may be
written; this file says what it claims, so a renderer draws it and a prover checks it the same way.

A document is a tree of levels from its root `level`; a node opens the level inside it. Each level has one kind, and
time means something different in each.

## Topology

Time does not matter: nodes are components that exist together, and an edge is a relation that holds between them,
read from source to target. A rule on a node or edge holds at every moment. A topology level is what a system is made
of; it answers "what is there, and what depends on what".

## Workflow

A run goes from its first activity to its last: nodes are activities, and an edge hands an artifact from one to the
next once the first is done, its `must` rules acting as guards. State lives only while a run goes. A fork starts
branches that run side by side, and a join waits until every branch has arrived; partitions say who does each
activity.

## State

One subject persists and moves between states: nodes are states, each the set of subject instances in it, and an edge
is an event that moves an instance from one state to the next. Each region holds every instance in exactly one of its
states, from its initial state on; regions change on their own and meet only through syncs, where an event in one
region, while a state holds, causes an event in another.

## Opening a level

A node that opens a level of another kind shows a different view of the same thing (`link: view`): a component's
workflow, an activity's states. A node that opens a level of its own kind refines it: the child's ports carry exactly
the parent node's edges, so what holds of the parent holds of the child; `link: nest` drops that claim.

## Metadata

`meta` annotates any document, level, node or edge without changing what it claims: reserved keys record a remark, a
change, the evidence it rests on and the requirement it serves, and any other key carries a value of the format its
name ends in.

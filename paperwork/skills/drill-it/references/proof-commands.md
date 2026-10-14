# The model in Alloy

`check-system.py alloy system.json out.als` writes one Alloy 6 module; the
`alloy` check runs it. Without Alloy `check` exits 3 (`alloy --fetch` downloads
it). A command unproved after 120 s (`PAPERWORK_ALLOY_SECONDS`): shrink or split its
rule; raise the limit only once, to confirm.

Passing means no counterexample within Scopes. Levels are not linked
(a level inside a node has its own moments).

## Translation

- component, artifact, outside type: `sig`; abstract: `abstract sig`; "is a": `extends` (two parents: `in A + B`); singleton: `one sig`
- attribute `T`, `T?`, `T[]`, `T[1..]`: field `one`, `lone`, `set`, `some`; `name: Bool`: subset `sig Name in Owner`
- relation: its field, or one named by its verb
- literal set: `enum`
- state level: each state a `var sig` subset of the subject; regions partition
- workflow level: `one sig <Title> { var at: set <Title>Step }` (active activities)
- change operation, event, trigger, artifact handed on: a `Call` kind: `self`, parameters, `result` fields
- `x.verb[args]`: that call is in `Now.happens`
- query operation: a receiver field: `Evals.score[skill]`
- rule: a lowerCamel `pred`

A moment is its calls (`Now.happens`); a sync's two events can share one. Frame
conditions on each region, run and `modifies` attribute: nothing changes without a call. An event happens only in a state with that edge.

## What Alloy is asked

Each passes when the first clause holds; else it reports the second.

- `consistent`: a run keeps every rule and makes a call; else rules contradict behaviour
- `independent_<rule>` (not guards): a run breaks only this rule; else the rule follows from the others
- `holds_<rule>` (must): no run breaks it; else a finding, not a problem (counterexample calls)
- `holds_<rule>` (should): no run breaks it; else a note: its counterexample
- `scenario_<slug>`: its walk can happen: on each workflow and state level, each step's edge call strictly after the previous (component levels: drawing only); else the Scenario cannot happen
- `reach_<edge>`: a failure path can be taken; else the failure can never happen

Rules split three ways ([model-writing.md](model-writing.md), Rules, says where each sits):
- A guard is behaviour.
- A rule over what changes (states, activities, calls, `modifies` attributes, time) is checked against the behaviour.
- Any other `must` is assumed; any other `should` is only required of the ideal run in `consistent`.

A failing `must` is a finding about the system: `check` prints a `finding` line, still ends `ok`. Hand it back; change the model only for your
mistake: a guard, `pre` or `post` it omits.

Plan `prove`: `rules` drops Scenarios and failure paths, `off` asks nothing.

## Scopes

Every command: `for 3`, 8 moments (`steps`). A Scenario: two moments per visit
on its longest level, plus three; an independence run, four. An abstract
component: three atoms per extending kind.

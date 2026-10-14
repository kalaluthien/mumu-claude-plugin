# The model in Alloy

`check-system.py check system.json --prove` runs Alloy once, at the last step,
and never fails the run. `alloy system.json out.als` writes the Alloy 6 module;
`alloy --fetch` downloads Alloy (needs Java). No Alloy, no Java, a refused
module or a command over 120 s (`PAPERWORK_ALLOY_SECONDS`) is a `note` and
ends `ok (unproved: reason)`; to prove, shrink or split that rule.

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

One question per dynamic rule, `holds_<rule>`: does any run break it?
- `must`: a run that does is a `finding` (the counterexample's calls), not a problem.
- `should`: a run that does is a `note`.

Rules split three ways ([model-writing.md](model-writing.md), Rules, says where each sits):
- A guard is behaviour.
- A rule over what changes (states, activities, calls, `modifies` attributes, time) is asked.
- Any other rule is assumed, not asked.

A finding is a defect of the system, not of the model: `check` prints a `finding` line and still ends `ok`. Hand it back; change the model only for your
mistake: a guard, `pre` or `post` it omits.

Plan `prove`: `rules` (default) asks the `holds_` commands, `off` nothing.

## Scopes

Every command: `for 3`, 8 moments (`steps`).

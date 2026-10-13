# The model in Alloy

`make-diagram.py alloy model.json out.als` writes the model as one Alloy 6 module,
and the `alloy` check runs it; without Alloy, `check` exits 3. A command
unproved after 120 s (`ZOOM_DIAGRAM_ALLOY_SECONDS`): shrink or split its rule;
raise the limit only to confirm once.

Passing means no counterexample within the Scopes below. The zoom levels are
not linked in the module: a level drawn inside a node is not tied to that
node's moments.

## Translation

The translation is deterministic, and formulas are copied as written.

| Model | Alloy |
|---|---|
| component, artifact, outside type | `sig`; abstract is `abstract sig`; "is a" is `extends` (two parents: `in A + B`); `singleton` is `one sig` |
| attribute `name: T`, `T?`, `T[]`, `T[1..]` | field with `one`, `lone`, `set`, `some`; `name: Bool` is a subset `sig Name in Owner` |
| relation | the field it stands for, or a field named by its verb |
| literal set | `enum` |
| state level | each state a `var sig` subset of the subject; regions, each a partition of the subject |
| workflow level | `one sig <Title> { var at: set <Title>Step }`: the activities active now |
| change operation, event, trigger, artifact handed on | a kind of `Call` with the receiver as `self`, the parameters and `result` as fields |
| `x.verb[args]` | a call of that kind is in `Now.happens` at this moment |
| query operation | a field on the receiver: `Evals.score[skill]` |
| rule | a `pred` named in lowerCamel |

Every moment is the set of calls made in it (`Now.happens`), so a sync's two
events can share a moment. Nothing changes without a call: each region, run and
`modifies` attribute has a frame condition. A call made where nothing handles
it is refused: an event happens only in a state with that edge.

## What Alloy is asked

| Command | Passes when | Problem it reports |
|---|---|---|
| `consistent` | some run keeps every rule and makes a call | rules and behaviour contradict each other |
| `independent_<rule>` (not guards) | a run breaks only this rule | the rule follows from the others |
| `holds_<rule>` (must) | no run breaks it | it can break, with the calls of its counterexample |
| `holds_<rule>` (should) | no run breaks it | a note only: its counterexample |
| `scenario_<slug>` | its walk can happen: on each workflow and state level, each step's edge call strictly after the one before (component levels are walked on the drawing only) | the Scenario cannot happen under the rules |
| `reach_<edge>` | a failure path can be taken | the failure can never happen |

Rules split three ways:
- A `must` on a workflow or state edge is a guard and part of the behaviour.
- A rule over things that change (states, activities, calls, `modifies`
  attributes, time) is checked against the behaviour.
- Any other `must` is assumed; any other `should` is only required of the
  ideal run in `consistent`.

So a `must` that fails its `holds_` check needs a mechanism: a guard on the
event, or an operation's `pre` or `post`.

The page shows each rule's standing and its counterexample. The plan's `prove` narrows what is asked: `rules` leaves out the Scenarios and
failure paths, `off` asks nothing.

## Scopes

Every command uses `for 3`, room
for every kind of call, and 8 moments (Alloy's `steps`). A Scenario gets two
moments per visit on its longest level, plus three; an independence run, four. In runs, an abstract
component gets three atoms per kind that extends it. The calls of a
counterexample are reported by the model's own names.

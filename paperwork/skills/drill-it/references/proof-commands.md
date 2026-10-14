# The model in Alloy

`check-system.py check system.json --prove` runs Alloy once, last; never fails. `alloy system.json out.als` writes the module; `alloy --fetch`
downloads it (needs Java). No Alloy or Java, a refused module, or a command
over 120 s (`PAPERWORK_ALLOY_SECONDS`) is a `note` and ends `ok (unproved:
reason)`; shrink or split that rule.

Passing means no counterexample within Scopes; levels are not linked.

## Translation

- component, artifact, outside type: `sig`; abstract: `abstract sig`; "is a": `extends` (two parents: `in A + B`); singleton: `one sig`
- attribute `T`, `T?`, `T[]`, `T[1..]`: `one`, `lone`, `set`, `some`; `name: Bool`: `sig Name in Owner`
- literal set: `enum`; rule: `pred`
- state level: each state a `var sig` subset of the subject
- workflow level: `one sig <Title> { var at: set <Title>Step }`
- change operation, event, trigger, handed-on artifact: a `Call` kind; `x.verb[args]` is in `Now.happens`
- query operation: a receiver field

## What Alloy is asked

Per dynamic rule, `holds_<rule>`: does any run break it? A `must` that does is a
`finding` (the counterexample's calls); a `should`, a `note`.

Rules ([model-writing.md](model-writing.md), Rules): a guard is behaviour; a
rule over what changes (states, activities, calls, `modifies`, time) is asked;
any other is assumed. Nothing changes without a call, and an event happens
only in a state with that edge.

A finding is a system defect; `check` still ends `ok`. Hand it back;
fix the model only for your mistake (an omitted guard, `pre`, `post`).

Plan `prove`: `rules` (default) asks them, `off` none.

## Scopes

All commands: `for 3`, 8 moments (`steps`).

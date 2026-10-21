# Prove

Check that a system holds the rules its Schema states, with Alloy 6, and show each broken rule as a run over the
Schema's own nodes and edges. Each rule is one property; Alloy asks whether any run within the scope breaks it.

## Language

The document is written in the grammar, [../schema/assets/schema.json](../schema/assets/schema.json), and the module
follows each kind's reading, so an edge means one thing in the drawing and in the proof:

- [Topology](../schema/semantics.md#topology): each component is a signature and each relation a field; nothing
  moves, so a rule here holds or fails in one state.
- [Workflow](../schema/semantics.md#workflow): the run is one atom whose active steps change; an edge fires only from
  an active step, a trigger or a port starts one, and a guard on an edge holds whenever it fires.
- [State](../schema/semantics.md#state): each state is a changing subset of the subject, one per region at a time;
  an event moves an instance only from a state that has that edge, and a sync makes its second event happen in the
  same step as its first.
- [Opening a level](../schema/semantics.md#opening-a-level): levels are not linked in the module, so a rule is proved
  over all levels at once, never across a refinement.

## Run

With no document yet, write the smallest one the ask's rule talks about: the level it names and the rule as a
`must`, in the grammar above, checked `ok` by
`${CLAUDE_PLUGIN_ROOT}/skills/zoom/references/schema/scripts/check-schema.py check <doc.json>`.

`${CLAUDE_PLUGIN_ROOT}/skills/zoom/references/playbook/scripts/prove-schema.py <doc.json>`
([prove-schema.py](scripts/prove-schema.py)) writes the module (its path on stderr; `--als <path>` to keep it) and
prints one line per rule. Alloy runs from `~/.cache/paperwork-alloy/alloy.jar` or `$ALLOY_JAR` with `java`; answers
are cached, so an unchanged rule is not run again.

| line | means | next |
| --- | --- | --- |
| `<rule>: pass` | no run in the scope breaks it | done; a pass proves nothing past the scope |
| `<rule>: counterexample <trace>` | a run breaks it | read the trace on the Schema; a `must` broken is a system defect: hand it back, and change the Schema only for a guard, pre or post you left out |
| `<rule>: unproved: <reason>` | no answer | run `prove-schema.py --fetch`, which downloads the pinned Alloy 6.2.0 jar, or split a rule past the time limit (`PAPERWORK_ALLOY_SECONDS`, 120 by default) |

A trace names Schema ids, as `check-schema.py ids` prints them: `[a, b]` are the nodes whose things witness the
break, then the elements called at each step, `→` between steps, ` + ` within one, and `x|y` where one call may be
either.

## Rules

- **Able to fail**: a pass you never saw fail proves nothing, so run `prove-schema.py --mutate <doc.json>` before
  handing over a pass. It checks each passing `must` again on copies that each drop one restriction (a sync, an
  operation's pre or post, a `must`) and ends its line `, fails without <id>, ...`, the restrictions that hold it, or
  `, unfalsified`, a rule that holds by the structure alone or says nothing: hand that one back as such. A guard's own
  slug in the list means only the guard holds the rule.

- **Every rule asked**: a guard on an edge holds by construction and passes; a rule over what never changes is asked
  under every other such `must`, so a counterexample says the structure alone does not force it.
- **Scope**: every check runs `for 3`, 8 steps and room for each kind of call; a rule's own scope is added to its
  check. Raise it only for a rule about large numbers.
- **Fixtures**: [regions-unsynced.json](fixtures/regions-unsynced.json) breaks `no-forbidden-pair`, and
  [regions-synced.json](fixtures/regions-synced.json), the same regions held apart by syncs, passes, and with
  `--mutate` fails without each sync; [pass-unforced.json](fixtures/pass-unforced.json) adds `one-car-state`, which
  one region forces, so `--mutate` prints it `unfalsified`. Run all three after changing the module.

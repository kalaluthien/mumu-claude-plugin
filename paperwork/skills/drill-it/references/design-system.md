# Design a system

Turn an intent for an unbuilt system into one checked buildable `system.json`.

**Order.** The order of the work is the order of the designed system's run:
start where something enters it (a person's goal, a request, a timer), decide
what handles it up to what it hands out, then take the next. Decide each
thing once, when the run first needs it, writing it then in the forms of
[model-writing.md](model-writing.md), mapped by [analyse-system.md](analyse-system.md)'s Order list. An open decision goes under `## Undecided` with your recommended option, which the model takes.

**Defects as you design.** Leave no Missing, Illegal, Redundant or Overloaded
state in a state level, and give each rule a mechanism (a guard, `pre`, `post`).

**Rebuild.** Someone given only `system.json` and the intent must build it without deciding: every path, branch, failure, value, limit and rule
goes in, on its own level past 7 nodes, and every thing the model keeps has
its whole life: what creates it, each change, and what ends it.

## Steps

1. `${CLAUDE_PLUGIN_ROOT}/skills/drill-it/scripts/check-system.py new system.json`; set plan.
2. Design per Order, one entry at a time, running `check-system.py check system.json --quick` after each.
3. Run the full check. A `finding` line is a hole in the design: close it with
   the rule's mechanism, or put it under Findings if it is the user's choice.

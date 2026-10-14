# Design a system

Turn an intent for a system not yet built into one checked `system.json`, a
design someone can build from.

**Order.** The order of the work is the order of the designed system's run:
start where something enters it (a person's goal, a request, a timer), decide
what handles it up to what it hands out, and take the next entry. Make each
decision once, when the run first needs it, and write it then in the forms of
[model-writing.md](model-writing.md), as
[analyse-system.md](analyse-system.md)'s Order table maps what you settle to
what you write. A decision the intent leaves open goes under `## Undecided`
with the option you recommend, and the model takes that option.

**Defects as you design.** Each state level you write has no Missing,
Illegal, Redundant or Overloaded state, and each rule has a mechanism that
keeps it (a guard, a `pre`, a `post`); settle that while writing the level,
not after.

**Rebuild.** The model holds every detail a rebuild needs: someone given only
`system.json` and the intent builds the system without deciding anything the
model leaves out. Every path, branch, failure, value, limit and rule goes in,
on a level of its own when a level would pass 7 nodes. Depth is the drawing's
choice, never a reason to leave a detail out.

## Steps

1. `${CLAUDE_PLUGIN_ROOT}/skills/drill-it/scripts/check-system.py new system.json`, then set the plan the caller passed.
2. Design the run as Order says, one entry at a time. Run
   `check-system.py check system.json --quick` after each entry is written.
3. When the run is written, run the full check. A `finding` line is a hole in
   the design: close it with the mechanism the rule needs, or hand it back
   under Findings when closing it is the user's choice.

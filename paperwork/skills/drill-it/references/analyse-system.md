# Analyse a system

Turn a system that exists (code, docs, configs, screens, a process people
run) into one checked `system.json`, and the defects it shows.

**Order.** The order of the work is the order of the system's own run: start
where something enters it (a command, a request, a timer, a person's goal),
follow it through what handles it to what it hands out, and take the next
entry. Read each source once, when the run first reaches it; while it is open,
write every model part it supports, in the forms of
[model-writing.md](model-writing.md):

| the source shows | write |
| --- | --- |
| an entry point | a trigger, and a Scenario whose first step starts there |
| a step of the run | the node it happens at, the edge it hands on, the Scenario's next step |
| a branch, a failure, a loop | the edge with its mark, and a Scenario for the branch |
| a thing and its fields | a component with `attrs`, the relations to what it points at |
| a lifetime (status, mode, phase) | a state level of its subject, its events |
| a function or call | an operation: signature, `pre`, `post`, `modifies` |
| a check, a guard, an invariant | a rule where it sits |
| a number, a limit, a timeout | a `qty`, or a `facts` item |

**Defects as you read.** When the source in hand shows a defect, write it
under `## Findings` then: a situation no state or path handles (Missing), a
state or call that should be impossible but is reachable (Illegal), two
states that react alike (Redundant), one state meaning two things
(Overloaded), a rule the system breaks. Model the system as it is, defect
included.

**Rebuild.** The model holds every detail a rebuild needs: someone given only
`system.json` rebuilds the system's behaviour without looking anything up.
Every path, branch, failure, value, limit and rule the sources show goes in,
on a level of its own when a level would pass 7 nodes. Depth is the drawing's
choice, never a reason to leave a detail out.

## Steps

1. `${CLAUDE_PLUGIN_ROOT}/skills/drill-it/scripts/check-system.py new system.json`, then set the plan the caller passed.
2. Follow the run as Order says, one entry at a time. Run
   `check-system.py check system.json --quick` after each entry is written.
3. When the run is written, run the full check. A `finding` line is a defect
   of the system: add it to Findings. Change the model only for your own
   mistake, where the model misstates what the system does.

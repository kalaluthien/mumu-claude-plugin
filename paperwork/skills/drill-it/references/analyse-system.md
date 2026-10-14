# Analyse a system

Turn an existing system (code, docs, configs, screens, a process) into one
checked `system.json` and its defects.

**Order.** The order of the work is the order of the system's own run: start
where something enters it (a command, a request, a timer, a person's goal),
follow it through what handles it to what it hands out, then take the next entry. Read each source once, when the run first reaches it (and what it imports
or calls), writing every
model part it supports, in the forms of [model-writing.md](model-writing.md):

- entry point: a trigger and a Scenario starting there
- step: its node, the edge it hands on, the Scenario's next step
- branch, failure, loop: the edge with its mark, a Scenario for the branch
- thing and fields: a component with `attrs` and relations
- lifetime (status, mode, phase): a state level of its subject, its events
- function, call: an operation: signature, `pre`, `post`, `modifies`
- check, guard, invariant: a rule there
- number, limit, timeout: a `qty`, or a `facts` item

**Defects as you read.** Write each defect under `## Findings` once its source
is open: a situation nothing handles (Missing), an impossible state or
call that is reachable (Illegal), two states that react alike (Redundant), one
state meaning two things (Overloaded), a rule the system breaks. Model the
system as it is, defects included.

**Rebuild.** Someone given only `system.json` must rebuild the behaviour of
the whole system the sources make up, not only the part the intent asks about;
the intent picks what the views feature. While a source is open, write every
path, branch, exit, failure, value, limit, name rule and check it shows into the
model, on its own level when a level would pass 7 nodes, else as a `facts` item. Never omit a detail for depth.

## Steps

1. `${CLAUDE_PLUGIN_ROOT}/skills/drill-it/scripts/check-system.py new system.json`; set the caller's plan.
2. Follow Order, one entry at a time; run `check-system.py check system.json` after each.
3. Run `check-system.py check system.json --prove` once. Add each `finding` line to Findings; change the model
   only where it misstates the system.

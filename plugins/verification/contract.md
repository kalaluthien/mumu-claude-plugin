# Contract

A change is checked against a contract that predates it, stated so that a check can fail.

| term | meaning |
| --- | --- |
| contract | what a change must keep: a relation that holds over a whole class of inputs, including what must not happen |
| path | the route an effect takes through the modules: which boundaries it crosses, in what order, and where it stops |
| spec | an Alloy model of the domain and the architecture: sigs, facts, one `check` per invariant; no scenarios |
| acceptance test | the app driven as its user drives it: the CLI, the HTTP API, the screen |
| integration test | one module against its real infrastructure: the database, the filesystem, the network |
| eval | cases run through an LLM system, each graded pass or fail by code or by a judge |
| failure mode | a way the system was seen failing in a trace, named for this product |
| layout | where a repo keeps its specs, tests or evals, and the command that runs them |
| bar | which checks a change must pass; the project's to set |

| role | does |
| --- | --- |
| owner | sets the bar and judges traces |
| agent | writes the checks and the change; never judges a trace on the owner's behalf |

Rules:

- Use the repo's layout. With none, initialise the default the skill names and tell the owner "no <kind> layout found; initialised <path>".
- Read the bar where the repo states it (CI, a contributing guide, agent instructions); with none stated, every check the change touches passes, and a number a skill gives is its default. Asked where verification stands, give each kind's layout, what it covers, its last result, and the gap to the bar.
- Write the check before the change and watch it fail for the reason the change addresses. One that has never failed is not evidence: break what it checks once, watch it fail, then restore.
- A check asserts a contract or a path, never one output byte for byte.
- A failing check is a defect in the change or the design. Never loosen a check, a fact or a scope to make it pass.
- The project's process is its own: these rules hold inside any order of work.

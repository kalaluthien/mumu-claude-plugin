# Contract

A change is checked against a contract that predates it, stated so that a check can fail.

| term | meaning |
| --- | --- |
| contract | what a change must keep: a functional relation, never one output byte for byte |
| spec | an Alloy model of the domain and the architecture: sigs, facts, one `check` per invariant; no scenarios |
| acceptance test | the app driven as its user drives it: the CLI, the HTTP API, the UI |
| integration test | one module against its real infrastructure: the database, the filesystem, the network |
| eval | cases run through an LLM system, each graded pass or fail by code or by a judge |
| failure mode | a way the system was seen failing in a trace, named for this product |
| layout | where a repo keeps its specs, tests or evals, and the command that runs them |

| role | does |
| --- | --- |
| owner | knows what good looks like: judges traces, and is told of every layout initialised |
| agent | writes the checks and the change; never judges a trace on the owner's behalf |

Rules:

- Use the repo's layout. With none, initialise the default the skill names and tell the owner "no <kind> layout found; initialised <path>".
- A check that has never failed is not evidence: break what it checks once, watch it fail, then restore.
- A failing check is a defect in the change or the design. Never loosen a check, a fact or a scope to make it pass.

# contract

Write a flow as one contract the checker accepts and a reader who never saw the sources can build or run the work from.

## Domain

A contract holds the records every paperwork contract holds, as [contract.md](../../../lib/contract.md) defines them: sources, terms, levels, tags, areas, claims, questions and parts. This skill adds nodes, edges, tasks, fragments and milestones, and gives each level a `kind` and its `nodes`.

- **top**: `title`, `purpose`, `sources`, `terms`, `areas`, `levels`, `nodes`, `edges`, `tasks`, `fragments`, `milestones`, `claims`, `questions`.
- **evidence**: nodes, edges, tasks, fragments, milestones, areas and claims take `evidence` and `basis`.
- **area**: the side a node belongs to, such as a team or a data centre; the page gives each area one colour and its label.
- **part**: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/flow/scripts/check-contract.py split <contract> <folder>` writes the parts: `top.json`, the areas and nodes included, its `levels` the level ids in order, and `levels/<id>.json`, one level with its edges, tasks, fragments and milestones; an edit goes into the one part file it changes.
- **level**: `kind` (`interaction` or `plan`) and `nodes` (the ids it draws, in order across the top or down the left); an edge opens it.
- **node**: `id`, `label`, `tag`, `area`, `purpose`, `info`: a system, an actor or a resource; one node may be drawn by several levels.
- **edge**: `id`, `level`, `from`, `to`, `label`, `tag`, `opens`, `after`, `info`. On an interaction it joins two nodes its level lists, or a node to itself for its own step, and its `work` item, a table of `area`, `change` and `says`, names what each area must build or change for it; its label the exchange as written, such as `GET /v1/names/{name}`, and its place in the list its place in time. On a plan it joins two tasks: a `request` asks the `to` task to start, a `wait` holds it until the `from` task ends.
- **task**: `id`, `level`, `node`, `label`, `tag`, `purpose`, `after`, `info`: one piece of work on a plan, drawn as a bar on its node's line.
- **fragment**: `id`, `level`, `kind` (`alt`, `opt`, `loop`, `par` or `break`), `operands`, each `{"guard", "edges"}`: a frame round edges of an interaction that follow one another; `alt` and `par` hold two operands or more, the others one, and every operand but a `par`'s says its guard.
- **milestone**: `id`, `level`, `label`, `after` (what it waits on), `purpose`: one point in time; what comes after it names it in its own `after`.
- **after**: the ids of the edges, tasks or milestones of the same level that come first. An interaction's edges also come in their list's order; a plan's tasks also follow the tasks their edges come from.

`${CLAUDE_PLUGIN_ROOT}/skills/flow/fixtures/name-lookup.json` is a whole interaction with a nested level, and `${CLAUDE_PLUGIN_ROOT}/skills/flow/fixtures/launch-plan.json` a whole plan.

## Steps

1. Write the questions a builder must answer: the order of the calls, each failure branch, the owner of each step, what blocks what, and what is still unknown.
2. Choose the levels: the whole flow first, an inner one only where a question lies inside one exchange, opened by that edge.
3. Write the areas and nodes, then the edges or tasks in time order, each with its tag's items, a `call` between two areas with its `failure` or `errors`; `python3 ${CLAUDE_PLUGIN_ROOT}/skills/flow/scripts/check-contract.py tags` prints them.
4. Frame each branch, option, repeat, parallel run and early exit as a fragment, and each point every later step waits on as a milestone.
5. Write the claims, each that does not hold with its `fault`, then answer each question by the records that answer it, or the claim whose `fault` says why none does.
6. Check: run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/flow/scripts/check-contract.py check <contract> --root <subject root>`, adding `--part <part>`, such as `--part levels/<id>`, to print only the breaks of each part edited; an edit can break another part that reads it, so take the contract as checked only when the whole check, or `make-page.py`, which checks again every part whose view the edit changed, prints no break; the `rules` call says what each rule asks.
7. Read the order: run the `order <contract>` call and correct each critical path or place that is false of the subject.
8. Measure: give the contract alone to a fresh subagent and ask it what it would have to guess to build or run the flow; each guess is a finding to add or a claim with a `fault` to record.

## Rules

- **Order is the record's**: time on an interaction is the edges' list order and `after`, on a plan the edges and `after`; no record holds a date or a duration.
- **Milestones hold**: nothing a milestone waits on comes after what waits on the milestone; the checker refuses such a crossing as `milestone-order`.
- **No drawing field**: no record holds a position, a colour or a size; the page's code decides them.

# Authoring

How to write a Schema document well. The grammar is [assets/schema.json](assets/schema.json), what each kind means is [semantics.md](semantics.md), and brackets name the rule that enforces a line (`scripts/check-schema.py rules`). Every name is English [vocabulary]: titles, labels, slugs (`Defining`, not `정하기`). Only descriptions, the sentences a person reads, are in the reader's language.

## Domain

Start from the question the document answers, in the plan's `intent`. A document changes the defaults only in its `plan`; say in `why` why each default was changed [form]. A drawing's own choices (views, depth, layout) live in its view file, never here.

### Vocabulary

Ids, slugs, operations and type names follow the grammar's patterns [name-pattern]. Names are unique across the model, ignoring case, spaces, `-` and `_`; only an edge's label may recur [unique-names]. No name is an Alloy keyword (`open`, `run`, `in`, `until`, `check`, …) or a translation word (`Now`, `Call`, `happens`, `at`, `self`, `result`) [vocabulary]. Forms by kind [naming]:
- Scenario: verb phrase with object (`land-change`); a branch: see Branches.
- Operation: method on what it changes (`PullRequest.merge`).
- Rule: a property (`least-privilege`).
- level: noun phrase for the whole (`Pull request lifecycle`).
- component: noun phrase; abstract may be an adjective or participle (`Hands-on`).
- partition: noun phrase for who or where (`Squad`).
- relation: present-tense verb, read from → to (`points to`).
- activity: verb in -ing (`Reviewing code`).
- artifact, workflow trigger: noun phrase (`checked model`).
- state: adjective or participle (`Merged`).
- event, state trigger: plain verb (`mark ready`).

## Scenarios

A Scenario is one independent question the model answers, walked over the nodes that answer it. It is a use ("When <actor> does X, Y happens") or a claim ("To see why <claim>, …") walked from the claim to what it rests on. None is a part of another or a union of others [basis]. Root Scenarios are the goals people bring to the whole system; other levels get Scenarios as the `scenarios` plan default says [scoped].

**Steps.** A Scenario's `walk` lists its steps, each `{"place", "does", "expects"}` [steps]:
- `place` is the node where the step happens, the first in the Scenario's own level. Leaving or entering a level may go along an edge of the node that opened it; if two fit, name one: `"edge": "label"`.
- On a component level a step may use several parts together: `"place": ["node", "argument", "value"]`, each next part along a relation.
- `does` says what happens; `expects` says what is true afterwards, checkable.

**Hand-written fixture.** A fixture passes `check-schema.py check` only with a Scenario whose `walk` steps through every node and edge, entering a child level by stepping from its opener to a child node [scoped, coverage]; each rule named in some node's `rules` [placement]; the main edges marked `happy` [paths]; and, for no `mechanism` warning, a topology level, such as a `link: view` opened from a state and walked by the root Scenario. `playbook/fixtures/` may keep that warning, `schema/fixtures/` may not, since `check-schema.py fixtures` wants a plain name accepted with no warning.

**Walk on a topology level.** A multi-part `place` lists node ids only, never relation names. The next step starts at a node one edge from the previous step's last node, never the same one. A step's `edge` names the label for every hop it takes, its inner path included, so put it on a one-node step; leaving to the opener and stepping in again is allowed. In `view.json` an edge `via` takes only `left`: two edges between the same pair overlap, so fold one into an attribute.

**Branches.** A choice between two ways, and a failure, is each its own Scenario. The usual way keeps the plain name; a branch adds what differs to it: `ship-a-bet`, `ship-a-bet-replan`.

**Forks.** A list in the walk holds two or more side-by-side branches, each a step, a list of steps, or `[]` (an edge straight to the join); the next step joins them: `[spec, [[plan, impl, review], []], validate]`.

## Levels

Pick the kind by what the reader follows ([semantics.md](semantics.md)): the parts, the activities of a run, or the life of one thing (a repository persists, but pushing it is a run). The kind is never shown.

Rules for a level:
- The model's `level` is the root, the system's outermost repeating structure. A node opens the level inside it with `opens`.
- Show what it is made of (components) and how it works (activities, states); a body of knowledge has claims and what they rest on [mechanism].
- A level has 2 to 7 nodes; group states that react alike and detail them below.
- Every edge says something: a `what`, an operation or a guard [explained].
- A condition such as "pass" is a guard, not an artifact: name what is handed on.
- An artifact that is a component shown elsewhere gets `is: <component id>`.
- A state level names its `subject`, the one thing whose states these are, each a subset of it. It gives `initial` (one state per region) and may give `init`, a formula true at the start.
- A component with exactly one instance (a harness, a policy) is `singleton`.

**Abstract components.** An `abstract` component (interface, trait, protocol, generic, base) is drawn dotted; a relation to it is plain `is`. It never depends on a concrete one [naming].

**Attributes and relations.** Components carry `attrs` as `name: Type`: `T` one, `T?` at most one, `T[]` any number, `T[1..]` at least one; `A | B` either, `(A, B)[]` pairs. `name: Bool` is a subset of the component (`ships: Bool` makes `Ships`). A relation is a field: the attribute that points at its target (name it with `attr` when two could), or else a field named by its verb (`runs on` is `runsOn`). An attribute that points at a component on the same level is drawn [typed].

**Triggers.** `triggers` on a workflow or state level bring something in from outside: a one-off arrival, or a repeating one with `every` (a clock). Requests at a rate are a one-off arrival, the rate in the `what`. A Scenario whose steps enter at the trigger's node uses it.

**Opening a level.** A node that opens a level of another kind is marked `link: view` [view-link-unmarked]. One that opens a level of its own kind refines it. Its ports list the parent's edges as `in` (to a node) and `out` (from a node, or a list when several hand on the same thing). Triggers count as inputs [opens-interface]. Mark it `link: nest` instead when the child is a closer look with no such claim [nest-unrefined]. What a root workflow hands out goes to a node of its own, such as the activity of whoever receives it [form].

**Gates.** A workflow node with `gate: fork` starts branches that run side by side, and one with `gate: join` waits for all of them [gates, join-without-fork].

## Paths and partitions

Marks:
- `happy`: the usual way through, on every workflow and state level [paths].
- `failure`: an edge or port where an activity fails, to where it goes; every gate (a label starting with checking, reviewing, validating, verifying, testing, judging, approving, gating or evaluating) has one [paths].
- `optional`: what happens only sometimes, or may not exist (dashed).
- none: a loop, the edge back to what repeats until something holds.

`unsure` marks what a source does not confirm ("?").

**Regions and syncs.** A state level's `regions` (each state's `region`) are orthogonal: parts of one thing that change state on their own (a branch on your machine and on GitHub). Use them instead of multiplying states; each starts in one initial state [region-without-initial]. They meet only through `syncs`: `{ "name", "when": event, "where": state, "then": event }`: a sync waits for its `when` event while its `where` state holds. Then its `then` event follows in another region [syncs, sync-unknown-transition].

**Superstates and history.** A state that opens a state level is a superstate: draw its states there, each event in or out on the superstate itself. Give that level `history` when entering again resumes where it was left, `shallow` for its own states, `deep` for every level below too; only a level opened from a state of its subject has it [history-outside-superstate]. Point a trigger from outside at the superstate, not at a child state other than the initial one, since the child's trigger fires only inside the superstate. Give an edge into a superstate `enters` when that edge alone starts afresh or resumes [enters-without-superstate]. Mark a state where a superstate's work ends `final`, with no edge out of it [final-with-exit], and give the edge that leaves once it ends `completion` [completion-without-final]; leave `completion` off when an outside event, not the ending, leaves the superstate.

**Partitions.** Give `partitions` for two or more answers to who does each activity, where each thing lives or what it may access, one criterion per level. Each partition forms one block: no node of another partition sits inside the rectangle that spans its nodes. A crossing edge's contract is a payload, a guard or an operation [partitions].

## Quantities

When how much matters, give the element a `qty` `{"value", "unit", "kind"}` [quantities]; skip decorative numbers. Kinds:
- `stock` (node): what it holds; flows use its unit per time (`GtC`, `GtC/yr`).
- `count` (node or edge): how many.
- `capacity` (node): at most this many.
- `flow` (edge): how much moves.
- `delay` (edge): a deadline; the source has an edge marked `failure`.

What must add up is in `check-schema.py rules` (quantities), checked only where every edge on that side says how much, in one unit. Curves, rates over time and queues are `example` media.

## Operations

An operation is a method, `Receiver.verb(name: Type, …) → Result` [typed].

- **Receiver**: What it changes, or, for a query, what it reads.
- **Inputs**: Every other input the result depends on is a named, typed parameter, even if the receiver points to it: `PullRequest.merge(base: Branch, method: MergeMethod) → Commit`.
- **Types** are exact names [typed]: a component (`Pull request` is `PullRequest`); an artifact, by any tail of its words, singular or as written (`checked model` is a `Model`); the run of a workflow (its title). Also exact: an outside type declared in `types` with one sentence; `Text`, `Url`, `Date`, `Number` or `Count`; a literal set such as `{merge, rebase}`, or one named in `types` as `"MergeMethod": "{merge, squash, rebase} One sentence."` when two places share it. Values are lowerCamel.
- **Where it sits** [placement]: a component's method. An activity's (it performs the activity; one of its operations returns what the activity hands on). A state's (it runs only while the subject is in that state). An event's or trigger's (an event carries one operation, its receiver the level's subject).
- **Change or query**: An operation on an activity, state or event, or naming what it `modifies` (`"Branch.tip"`), is a call at one moment; any other is a query, a function the model reads.
- **Conditions**: A precondition holds when it is called and a postcondition after, over `self`, its parameters and `result`; the modified list names exactly the attributes the call may change.
- **One per verb**: Open, up and jump are all `Board.goto`. Write the signature before the sentence.

## Rules

A rule is a proposition no other rule implies; Alloy checks once that it holds.

- **Where it sits**: On a node it holds the whole time. On an edge or trigger of a workflow or state level, a `must` is the guard: the artifact is handed on, or the event happens, only when it holds.
- **Kind**: `must` (breaking it breaks a result) or `should` (makes things worse).
- **Formulas are Alloy 6** over the module's names [vocabulary]: predicate, relational, integer and temporal (`always`, `eventually`, `after`, `once`, `until`, `;`). Keywords are words: `not`, `and`, `or`, `implies`, `iff`, `else`.
  - `x.attr` for a member, `x.verb[args]` for "that call happened now", `x.verb` for any call of it; a state's name is the set of things in it; another rule is a predicate by its lowerCamel name.
  - Values are names, not strings: `review.verdict = approve`. The next state is written with `after`, never a prime.
  - Variables are named like code, never one letter, never a name of the module: `all pr: PullRequest, review: pr.reviews | review.author != pr.author`.
- **Scope**: A rule about large numbers (`#nodes =< 7`) names the scope that can break it, as `"scope": "12 Drawn, 5 Int"`.
- **Scenarios**: A Scenario does not list the operations and rules on what its steps walk [coverage].

## Text and media

- A level's `why` says what it shows.
- Every description is plain, full sentences: first what it is for, then what follows. Never fragments or a repeat of the drawing.
- Add `refs` as `[name](url)` wherever a source exists. Never invent a URL.

Add `media` when something concrete explains faster than a sentence. Types:
- nodes and edges: `example`, `code`, `facts` (`[term, sentence]` items), `quote` (with `refs`), `pitfall`.
- nodes only: `tree` (two spaces per depth), `checklist` (what must be true when it is done).
- edges only: `payload` (what travels along it), `diff` (`before` and `after`, drawn as a line diff).
- anywhere, one per level: `insight`.

An `insight` points out what is distinctive about this system, not what it does:
- `move`: the design choice;
- `vs`: the usual design it departs from, a real practice, not a strawman;
- `gain`: what the move buys;
- `rule`: the operation or rule that holds the move in place, on the same node or edge (on a level, any rule).

Write none when nothing is distinctive.

Give edges media as readily as nodes. Mark made-up media `invented: true` (shown as "e.g."). Give a `title` only when it says more than the type. Never draw an order of activities in a note; it is a level.

## Metadata

`meta` on a document, level, node or edge holds what the drawing does not. Under the grammar's reserved keys it holds a remark, a change, the evidence it rests on (each a `path:line`, a url or a sha) and the requirement it serves (each `<path or url>#<requirement>`). Under any other key named `<name>-<format>`, it holds a value fitting that format [meta-key, meta-format, evidence-pointer, constraint-id]. The formats are the keys of the grammar's `$defs.format`.

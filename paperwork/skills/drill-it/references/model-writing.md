# Model writing

Brackets name the check that enforces a line ([proof-commands.md](proof-commands.md)).
Every name is English whatever the reader's language, since Alloy sees it too
[vocabulary]: titles, labels, slugs (`Defining`, not `정하기`). Only descriptions
(`what`, `why`, `text`, `intent`, a step's `does` and `expects`) are in the
reader's language.

## Plan

A model changes the defaults only in its `plan` (`check-system.py rules` lists
them; `check-system.py plan system.json` prints the plan in effect). Say in `why` why each changed default was changed [form]. A drawing's own choices (views, depth,
layout) live in its view file.

## Scenarios

A Scenario is one independent question the model answers, walked over the
nodes that answer it: a use ("When <actor> does X, Y happens") or, for a body
of knowledge, a claim ("To see why <claim>, …"), walked from the claim to what
it rests on. None is a part of another or a union of others [basis].

Root Scenarios are the goals people bring to the whole system; other levels
get Scenarios as the `scenarios` plan default says [scoped].

**Steps.** A Scenario's `walk` lists its steps, each
`{"place", "does", "expects"}` [steps]:
- `place` is the node where the step happens, the first in the Scenario's own
  level. Leaving a level may go straight along an edge of the node that opened
  it, entering straight along an edge into that node. When two edges could be
  taken, name one: `"edge": "label"`.
- On a component level a step may use several parts together:
  `"place": ["node", "argument", "value"]`, each next part along a relation.
- `does` says what happens; `expects` says what is true once it is done, in
  words a reader can check.

**Branches.** A choice between two ways, and a failure, is each its own
Scenario. The usual way keeps the plain name; a branch adds what differs to the
name of the Scenario it leaves: `ship-a-bet`, `ship-a-bet-replan`.

**Forks.** Things that happen side by side: a list in the walk holds two or
more branches, each a step, a list of steps, or `[]` for an edge straight to
the join, and the next step joins them:
`[spec, [[plan, impl, review], []], validate]`.

## Levels

| Level kind (never shown) | Node | Edge, named after |
|---|---|---|
| `schema`: nothing that changes over time matters | component | relation |
| `workflow`: state lives only while a run goes | activity | artifact handed on |
| `state`: state persists and can be counted | state | event |

Pick the kind by what the reader follows: the activities of a run, or the life
of one thing. A repository persists, but pushing it is a run.

- The model's `level` is the root, the system's outermost repeating
  structure. A node opens the level drawn inside it with `opens`.
- Show what it is made of (components) and how it works (activities, states).
  Where nothing runs (a body of knowledge) the nodes are claims and what
  they rest on [mechanism].
- A level has 2 to 7 nodes, which a drawing checks. Too many states? Group those that react
  alike and detail them below.
- Every edge says something: a `what`, an operation or a guard [explained].
- A condition such as "pass" is not an artifact: name what is handed on and
  make the condition its guard.
- An artifact that is a component shown elsewhere gets `is: <component id>`.
- A state level names its `subject`, the one thing whose states these are; each
  state is a subset of it. It gives `initial`, one state per region (below), and
  may give `init`, a formula true at the start.
- A component with exactly one instance (a harness, a policy) is `singleton`.

**Abstract components.** A component marked `abstract` is drawn dotted (an
interface, trait, protocol, generic or base). A relation to an abstract one is
"is a", so plain `is` will do. An abstract component never depends on a concrete one [naming].

**Attributes and relations.** Components carry `attrs` as `name: Type`: `T`
one, `T?` at most one, `T[]` any number, `T[1..]` at least one; `A | B`
either, `(A, B)[]` pairs. `name: Bool` is a subset of the component (`ships:
Bool` makes `Ships`). A relation is a field: it stands for the attribute that
points at its target (name it with `attr` when two could), or else becomes a
field named by its verb (`runs on` is `runsOn`). An attribute that points at a
component on the same level is drawn [typed].

**Triggers.** `triggers` on a workflow or state level bring something in from
outside: a one-off arrival, or a repeating one with `every`, a timer the system
keeps (drawn as a clock). Requests sent at a rate are a one-off arrival, the
rate in the `what`. A Scenario whose steps enter at the trigger's node uses it.

**Ports.** A workflow opened from an activity lists the parent's artifacts as
`in` (to a node) and `out` (from a node, or a list of nodes when several
activities hand on the same thing). Triggers count as inputs, and a port wears
its artifact's marks. They are drawn as ports on the level's edge [balanced].
What a root workflow hands out goes to a node of its own, such as the activity
of whoever receives it [form].

## Paths and partitions

| Mark | On |
|---|---|
| `happy` | the usual way through, on every workflow and state level [paths] |
| `failure` | an edge or port where an activity fails, to where the failure goes; every gate (a label starting with checking, reviewing, validating, verifying, testing, judging, approving, gating or evaluating) has one [paths] |
| `optional` | what happens only sometimes, or may not exist (dashed) |
| none | a loop: the edge back to what repeats until something holds |

A `failure` path is drawn dash-dot in the one warning ink and `happy`
heavier; `unsure` marks what a source does not confirm ("?").

**Regions and syncs.** A state level's `regions` (each state's `region`) are
orthogonal: parts of one thing that change state on their own, such as a
branch on your machine and on GitHub.

- Regions meet only through `syncs`:
  `{ "name", "when": event, "where": state, "then": event }`. When the
  `when` event happens and the `where` state holds, the `then` event in
  another region follows [syncs].
- Use regions instead of multiplying states.

**Partitions.** Give `partitions` when there are two or more answers to who
does each activity, where each thing lives or what it may access, one
criterion per level. Each partition forms one block: no node of another partition sits inside the
rectangle that spans its nodes. A crossing edge's contract is a payload, a
guard or an operation [partitions].

## Quantities

When how much matters to the reader, give the element a `qty`
`{"value", "unit", "kind"}`, drawn as a small figure beside it [quantities].
Leave it out where a number would only decorate.

| Kind | On | Means |
|---|---|---|
| `stock` | node | what it holds; flows use its unit per time (`GtC`, `GtC/yr`) |
| `count` | node or edge | how many |
| `capacity` | node | at most this many |
| `flow` | edge | how much moves |
| `delay` | edge | a deadline: the source has an edge marked `failure` for when it passes |

What must add up is in `check-system.py rules` (quantities). Sums are checked only where every edge on that side says how much, in one
unit. Curves, rates over time and queues are `example` media.

## Operations

An operation is a method, `Receiver.verb(name: Type, …) → Result` [typed].

- **Receiver.** What the operation changes, or, for a query, what it reads.
- **Inputs.** Every other input the result depends on is a named, typed
  parameter, even if the receiver points to it:
  `PullRequest.merge(base: Branch, method: MergeMethod) → Commit`.
- **Types** are exact names [typed]:
  - a component (label in UpperCamel: `Pull request` is `PullRequest`);
  - an artifact, by any tail of its words, singular or as written (`checked
    model` is a `Model`, `model.json` too);
  - the run of a workflow (its title), or an outside type declared in `types`
    with one sentence;
  - `Text`, `Url`, `Date`, `Number` or `Count`;
  - a literal set such as `{merge, rebase}`, or one named in `types` as
    `"MergeMethod": "{merge, squash, rebase} One sentence."` when two places
    share it; values are lowerCamel.
- **Where it sits** [placement]:
  - Component: that component's method.
  - Activity: it performs the activity; one of the activity's operations
    returns what the activity hands on.
  - State: it runs only while the subject is in that state.
  - Event or trigger: it is that event; an event carries one operation, its
    receiver the level's subject.
- **Change or query.** An operation on an activity, state or event, or naming
  what it `modifies` (`"Branch.tip"`), is a call at one moment. Any other is a
  query: a function the model reads.
- **Conditions.** `pre` holds when it is called and `post` after, over `self`,
  its parameters and `result`; `modifies` lists every attribute the call may
  change, and nothing else does.
- **One per verb.** Drop compositions: open, up and jump are all `Board.goto`.
  Write the signature before the sentence.

## Rules

A rule is a proposition no other rule implies; Alloy looks for a run that
breaks it ([proof-commands.md](proof-commands.md)).

- **Where it sits.** On a node it holds the whole time. On an edge or trigger
  of a workflow or state level, a `must` is the guard: the artifact is handed
  on, or the event happens, only when it holds.
- **Kind.** `must` (breaking it breaks a result) or `should` (makes things worse).
- **Formulas are Alloy 6** over the module's names [vocabulary], with every
  logic it has: predicate, relational, integer and temporal (`always`,
  `eventually`, `after`, `once`, `until`, `;`). Keywords are words: `not`,
  `and`, `or`, `implies`, `iff`, `else`.
  - `x.attr` for a member, `x.verb[args]` for "that call happened now",
    `x.verb` for any call of it; a state's name is the set of things in it;
    another rule is a predicate by its lowerCamel name.
  - Values are names, not strings: `review.verdict = approve`. The next state
    is written with `after`, never a prime.
  - Variables are named like code, never one letter, never a name of the
    module: `all pr: PullRequest, review: pr.reviews | review.author !=
    pr.author`.
- **Scope.** A rule about large numbers (`#nodes =< 7`) names the scope that
  can break it, as `"scope": "12 Drawn, 5 Int"`.
- **Scenarios.** A Scenario does not list the operations and rules on what
  its steps walk [coverage].

## Names

Names are unique across the model, ignoring case, spaces, `-` and `_`; only
an edge's label may recur [unique-names]. No name is an Alloy keyword (`open`,
`run`, `in`, `until`, `check`, …) or a translation word (`Now`, `Call`,
`happens`, `at`, `self`, `result`) [vocabulary]. Each kind has its own
form [naming]:

| Kind | Form | Example |
|---|---|---|
| Scenario | verb phrase with object; a branch: see Branches | `land-change` |
| Operation | method on what it changes | `PullRequest.merge` |
| Rule | a property | `least-privilege` |
| level | noun phrase for the whole | `Pull request lifecycle` |
| component | noun phrase; abstract may be an adjective or participle | `Commit`, `Hands-on` |
| partition | noun phrase for who or where | `Squad` |
| relation | present-tense verb, read from → to | `uses`, `points to` |
| activity | verb in -ing | `Reviewing code` |
| artifact, workflow trigger | noun phrase | `checked model` |
| state | adjective or participle | `Merged` |
| event, state trigger | plain verb | `merge`, `mark ready` |

## Text and media

### Sentences

- A level's `why` says what it shows.
- Every `what`, `why` and `text` is plain, full sentences: first what it is
  for, then what follows from it. Never terse fragments or a repeat of the drawing.
- Add `refs` as `[name](url)` wherever a source exists. Never invent a URL.

### Media

Add `media` when something concrete explains faster than a sentence.

| Where | Types |
|---|---|
| nodes and edges | `example`, `code`, `facts` (`[term, sentence]` items), `quote` (with `refs`), `pitfall` |
| nodes only | `tree` (two spaces per depth), `checklist` (what must be true when it is done) |
| edges only | `payload` (what travels along it), `diff` (`before` and `after`, drawn as a line diff) |
| anywhere, one per level | `insight` |

- Give edges media as readily as nodes. Mark made-up media `invented: true`
  (the reader sees "e.g."). Give a `title` only when it says more than the type.
- Never draw an order of activities in a note; such an order is a level.

## Insight

An insight points out what is distinctive about this system, not what it does:

- `move`: the design choice;
- `vs`: the usual design it departs from, a real practice, not a strawman;
- `gain`: what the move buys;
- `rule`: the operation or rule that holds the move in place, on the same node
  or edge (an insight on a level may name any rule).

Write none when nothing is distinctive. Example: diff against the merge base
(`move`), not the base tip, where a two-dot diff shows others' merges as
changes (`vs`), so the review holds still while the base moves (`gain`); the
rule is `three-dot`.

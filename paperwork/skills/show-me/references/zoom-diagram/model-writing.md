# Model writing

Brackets name the check that enforces a line. Every name below is also the
name Alloy sees ([proof-commands.md](proof-commands.md)).

## Plan

A model changes the defaults only in its `plan` (`make-diagram.py rules` lists
them; `make-diagram.py plan model.json` prints the plan in effect). Say in `why`
why each changed default was changed [form].

**Views.** Name the diagrams someone who works in this domain would look for
first: an ER model and the API for a backend, page navigation for a front end,
a CONSORT flow for a trial, the method and the claims for a paper. Each is
drawn by a level, `{"name", "level"}`, or left out with a reason,
`{"name", "why"}` [form]. A view no level can draw is a level you have not yet
opened, or a reason to give.

| Intent | Typical plan |
|---|---|
| explain the system to a newcomer | `depth: overview`, `prove: off` |
| audit one part | `deep` that part, `shallow` the rest, `prove: rules` |

**Depth.** `depth` is `overview` (root and one level), `working` (default) or
`detailed` (also: every operation is one action someone can do or point to).
At `working`, open a node when either holds:
- **A Scenario or a rule lives inside.** The reader needs its inside to follow
  a Scenario, or a `must` rule is kept there.
- **A design decision lives inside.** It is hard or likely to change and sets
  what the system can do (Parnas), so an insight could be written about it.
  Machinery many cases share is drawn once.

Stop when either holds:
- **Only what the intent can ignore is left.** It would vanish with perfect
  technology (McMenamin and Palmer: infinite memory and speed, nothing
  fails), or it is a library used unchanged, and the intent is not about it.
  Caching, failure, distribution and deployment are the system when the
  intent asks about them.
- **Only the cases differ.** Open the most distinctive case and list the rest
  as `facts`.

`deep` and `shallow` overrule these rules node by node.

## Scenarios

A Scenario is one independent question the model answers, walked over the
nodes that answer it: a use ("When <actor> does X, Y happens") or, for a body
of knowledge (a paper, a theory, a field), a claim ("To see why <claim>, …").
Find candidates in the passes below, then drop any that is a part of another
or a union of others [basis]. Stop when a pass adds nothing.

1. Actor goals (Cockburn): every actor, other systems included, and every
   goal that ends in one result.
2. Event sweep (McMenamin and Palmer): every outside, timed or state-change
   event. An event that no candidate answers is a missing Scenario.
3. Lifecycle gaps (CRUD): for each record, ask only about the empty create,
   read, change or retire cells.
4. Claims: every claim a reader comes to check, walked from the claim to
   what it rests on.

Root Scenarios are the goals people bring to the whole system. A level that
things enter from outside (a trigger) gets the Scenarios that start there; with
`scenarios: every`, each inner level gets the Scenarios of its own component or
workflow [scoped].

**Steps.** A Scenario's `walk` lists the steps of one walk, written as the
Scenario is found, each `{"place", "does", "expects"}` [steps]:
- `place` is the node where the step happens. The first starts in the
  Scenario's own level; each next one follows one edge in its direction, or
  steps into or out of an opened node. Leaving a level may go straight along
  an edge of the node that opened it, and entering one straight along an edge
  into that node. When two edges could be taken, name one: `"edge": "label"`.
- A component level has no time, so one step uses several of its parts
  together: `"place": ["node", "argument", "value"]`, each next part along a
  relation. Order lives in workflow and state levels.
- `does` says what happens in this step of this Scenario; `expects` says what
  is true once it is done, in words a reader can check.

**Branches.** A choice between two ways is two Scenarios, and so is a failure.
The usual way keeps the plain name; a branch adds what differs to the name of
the Scenario it leaves, so its slug says where it splits off: `ship-a-bet` and
`ship-a-bet-replan`, `open-a-model` and `open-a-model-pytorch`.

**Forks.** Things that happen side by side are a fork: a list in the walk
holds two or more branches, each a step, a list of steps, or `[]` for an edge
straight to the join, and the next step joins them:
`[spec, [[plan, impl, review], []], validate]`, each name standing for a step.

## Levels

| Level kind (never shown) | Node | Edge, named after |
|---|---|---|
| `schema`: nothing that changes over time matters | component | relation |
| `workflow`: state lives only while a run goes | activity | artifact handed on |
| `state`: state persists and can be counted; give `subject` and `initial` | state | event |

Pick the kind by what the reader follows: the activities of a run (workflow), or the
life of one thing (state). A repository persists, but pushing it is a run.

- The model's `level` is the root, the system's outermost repeating
  structure. A node opens the level drawn inside it with `opens`.
- Show what it is made of (components) and how it works (activities, states).
  Every root Scenario walks an activity or state, and every component appears
  in one, unless nothing in the model runs: a body of knowledge is claims and
  what they rest on [mechanism].
- A level has 2 to 7 nodes [size]. Too many states? Group those that react
  alike and detail them below.
- Every edge says something: a `what`, an operation or a guard [explained].
- A condition such as "pass" is not an artifact. Name what is handed on and
  make the condition its guard.
- An artifact that is a component shown elsewhere gets `is: <component id>`.
- A state level names its `subject`, the one thing whose states these are; each
  state is a subset of it. A level may give `init`, a formula true at the start.
- A component with exactly one instance (a harness, a policy) is `singleton`.

**Abstract components.** A component marked `abstract` is drawn dotted. It is
an interface, trait, protocol, generic or base; which one does not matter. A
relation from a component to an abstract one is "is a", so plain `is` will do.
An abstract component never depends on a concrete one [naming].

**Attributes and relations.** Components carry `attrs` as `name: Type`, as in a
UML class. The type says how many: `T` one, `T?` at most one, `T[]` any number,
`T[1..]` at least one; `A | B` either, `(A, B)[]` pairs. `name: Bool` is a
subset of the component (`ships: Bool` makes `Ships`). A relation is a field:
it stands for the attribute that points at its target (name it with `attr` when
two could), or else becomes a field named by its verb (`runs on` is `runsOn`).
An attribute that points at a component on the same level is drawn [typed].

**Triggers.** `triggers` on a workflow or state level bring something in from
outside: a one-off arrival, or a repeating one with `every`. `every` is a
timer the system keeps and is drawn as a clock; requests that people or other
systems send at a rate are a one-off arrival, their rate in the `what`. Any
Scenario whose steps enter that level at the trigger's node uses it.

**Ports.** A workflow opened from an activity lists the parent's artifacts as
`in` (to a node) and `out` (from a node, or a list of nodes when several
activities hand on the same thing, such as a failure report from each check).
Triggers count as inputs, and a port wears its artifact's marks.
They are drawn as ports on the level's edge [balanced] (DFD balancing). Any
other workflow, the root included, has no parent artifacts: what comes from
outside is a trigger, and what it hands out goes to a node of its own, such
as the activity of whoever receives it [form].

## Paths and partitions

Ask these of every level. Draw each answer that is true of the system; leave
out any that would be forced.

| Ask | Draw |
|---|---|
| What is the usual way through? | mark it `happy` on every workflow and state level [paths] |
| Where can an activity fail, and where does the failure go? | an edge or port marked `failure`. Every gate, a node whose label starts with checking, reviewing, validating, verifying, testing, judging, approving, gating or evaluating, shows one [paths] |
| What repeats until something holds? | the edge back, as a loop |
| What happens only sometimes, or may not exist? | mark it `optional` (dashed) |

A `failure` path is drawn in the one warning ink and `happy` heavier; `unsure`
marks what a source does not confirm ("?").

**Regions and syncs.** A state level's `regions` (each state's `region`) are
orthogonal regions (Harel): parts of one thing that change state at the same time and on their
own, such as a branch on your machine and the same branch on GitHub.

- Give `initial` one state per region.
- Events stay inside their region.
- Regions meet only through `syncs` (Meng and Jackson):
  `{ "name", "when": event, "where": state, "then": event }`. When the
  `when` event happens and the `where` state holds, the `then` event in
  another region follows [syncs].
- Use regions instead of multiplying states: two regions of two states each
  replace four combined states.

**Partitions** follow UML activity partitions and BPMN lanes. Give
`partitions` when there are two or more answers to who does each activity,
where each thing lives or what it may access (local and remote, people and
agents). Use one criterion per level. Every node belongs to one partition, and each partition
forms one block: no node of another partition sits inside the rectangle that
spans its nodes. On a workflow level, an edge that crosses
partitions needs a contract: a payload, a guard or an operation
[partitions].

## Quantities

When how much matters to the reader (people in a trial, money in a payment,
carbon in a reservoir, days to answer), give the element a `qty`
`{"value", "unit", "kind"}`; it is drawn as a small figure beside it
[quantities]. Leave it out wherever a number would only decorate.

| Kind | On | Means |
|---|---|---|
| `stock` | node | what it holds |
| `count` | node or edge | how many |
| `capacity` | node | at most this many |
| `flow` | edge | how much moves |
| `delay` | edge | it happens within this time: a deadline |

Curves, rates over time and queues are `example` media.

## Operations

An operation is a method, `Receiver.verb(name: Type, …) → Result` [typed].

- **Receiver.** The receiver is what the operation changes, or, for a query,
  what it reads.
- **Inputs.** Every other input the result depends on is a named, typed
  parameter, even when the receiver points to it:
  `PullRequest.merge(base: Branch, method: MergeMethod) → Commit`.
- **Types** are exact names [typed]:
  - a component (its label in UpperCamel: `Pull request` is `PullRequest`);
  - an artifact, by any tail of its words, singular or as written (`checked
    model` is a `Model`, `model.json` too);
  - the run of a workflow (its title), or an outside type declared in `types`
    with one sentence;
  - `Text`, `Url`, `Date`, `Number` or `Count`;
  - a literal set such as `{merge, rebase}`, or one named in `types` as
    `"MergeMethod": "{merge, squash, rebase} One sentence."` when two places
    share it. Values are lowerCamel names.
- **Where it sits** [placement]:
  - On a component, it is that component's method.
  - On an activity, it performs the activity, and one of the activity's
    operations returns what the activity hands on.
  - On a state, it runs only while the subject is in that state.
  - On an event or trigger, it is that event; an event carries one operation,
    and its receiver is the level's subject.
- **Change or query.** An operation that sits on an activity, state or event,
  or names what it `modifies` (`"Branch.tip"`), is a call that happens at one
  moment. Any other operation is a query: a function the model reads.
- **Conditions.** `pre` holds when it is called and `post` after, written over
  `self`, its parameters and `result`. Write the next state with `after`;
  `modifies` lists every attribute the call may change, and nothing else does.
- **One per verb.** Keep one operation per verb and drop compositions: open,
  up and jump are all `Board.goto`. Write the signature before the sentence.

## Rules

A rule is a proposition that no other rule implies; Alloy looks for a
run that breaks only it ([proof-commands.md](proof-commands.md)).

- **Where it sits.** On a node it holds the whole time. On an edge or trigger
  of a workflow or state level, a `must` is the guard: the artifact is handed
  on, or the event happens, only when it holds.
- **Kind.** It is `must` (breaking it breaks a result) or `should` (breaking it
  makes things worse).
- **Formulas are Alloy 6** over the module's names [vocabulary], with every
  logic it has: predicate, relational (`.`, `~`, `^`, `->`, `+`, `&`, `-`,
  `#`), integer and temporal (`always`, `eventually`, `after`, `once`, `until`,
  `;`). Keywords are words: `not`, `and`, `or`, `implies`, `iff`, `else`.
  - `x.attr` for a member, `x.verb[args]` for "that call happened now", and
    `x.verb` with no arguments for any call of it; a state's name is the set of
    things in it; another rule is a predicate by its lowerCamel name.
  - Values are names, not strings: `review.verdict = approve`.
  - The next state is written with `after`, never a prime.
  - Variables are named like code, never one letter, and never hide a name of
    the module: `all pr: PullRequest, review: pr.reviews | review.author !=
    pr.author`.
- **Scope.** A rule about large numbers (`#nodes =< 7`) names the scope that
  can break it, as `"scope": "12 Drawn, 5 Int"`.
- **Scenarios.** A Scenario uses the operations and rules that sit on what
  its steps walk; it does not list them [coverage].

## Names

Names are unique across the model, ignoring case, spaces, `-` and `_`; only
an edge's label may recur, since one verb or one artifact can appear many
times [unique-names]. No name is an Alloy keyword (`open`, `run`, `in`, `until`,
`check`, …) or a word the translation declares (`Now`, `Call`, `happens`, `at`,
`self`, `result`) [naming]. Each kind has its own form [naming]:

| Kind | Form | Example |
|---|---|---|
| Scenario | verb phrase with object; a branch: see Branches | `land-change`, `ship-a-bet-replan` |
| Operation | method on what it changes | `PullRequest.merge` |
| Rule | a property | `least-privilege` |
| level | noun phrase for the whole | `Pull request lifecycle` |
| component | noun phrase; abstract may be an adjective or participle | `Commit`, `Hands-on` |
| partition | noun phrase for who or where | `Squad` |
| state | adjective or participle | `Merged` |

The rest (relation, activity, artifact, event, trigger) is named after the
Levels table, and the lint prints the form it wants.

## Layout

Leave `x` and `y` out and the engine places each node beside a placed
neighbour, where its edges cross the fewest nodes and partitions stay blocks.
Set them when a place means something or when `fits` fails (the root first: it
must fit 390 px): a small grid where neighbours share a row or column, a busy
node goes in the middle, and two or three columns is usual. An edge between diagonal cells needs one empty corner.
A long edge down a column runs on its right; give it `via: "left"` when the
right is busy.

## Text and media

### Sentences

- A level's `why` says what it shows.
- Every `what`, `why` and `text` is plain, full sentences: first what it is
  for, then what follows from it.
- Never terse fragments, and never a repeat of the drawing.
- Add `refs` as `[name](url)` wherever a source exists. Never invent a URL.

### Screens

When people use the system through a screen, mock that screen in `screens`
and give `ui: {screen, block}` to every node the screen shows: a part of it, a
state it is in, or an activity whose result appears on it. Its
note then shows the screen with that block picked out. Do this on every
level whose nodes are parts of a screen, not only the first one you draw.

A mock predicts what the real screen looks like, so build it from the source,
not from memory of similar apps:
- Read the code that draws the screen (templates, components, styles,
  resource and string files) and take its regions, their order, and its
  visible text verbatim: titles, button labels, menu items, empty states.
- Keep the real layout: what sits beside what, what scrolls, which control is
  primary. Pick the block type that the code renders (`tabs`, `list`,
  `button`, `choices`, …).
- With no code, use the product's screenshots or documentation; a screen you
  had to guess is `invented: true` and reads "e.g.".

### Media

Add `media` when something concrete explains faster than a sentence.

| Where | Types |
|---|---|
| nodes and edges | `example`, `code`, `facts` (`[term, sentence]` items), `quote` (with `refs`), `pitfall` |
| nodes only | `tree` (two spaces per depth), `checklist` (what must be true when it is done) |
| edges only | `payload` (what travels along it), `diff` (`before` and `after`, drawn as a line diff) |
| anywhere, one per level | `insight` |

- Give edges media as readily as nodes.
- Mark made-up media `invented: true`; the reader sees "e.g.".
- Give a `title` only when it says more than the type does.
- Never draw an order of activities in a note; such an order is a level.

### Insight

An insight points out what is distinctive and clever about this system, not
what it does. It has four parts:

- `move`: the design choice;
- `vs`: the usual design it departs from, which must be a real practice and
  not a strawman;
- `gain`: what the move buys;
- `rule`: the operation or rule that holds the move in place. The rule
  must sit on the same node or edge; an insight on a level may name any rule.

Write none when nothing is distinctive. A restated description is not an
insight.


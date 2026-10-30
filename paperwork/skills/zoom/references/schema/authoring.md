# Authoring

How to write a Schema document well. The grammar is [assets/schema.json](assets/schema.json), what it means is [semantics.md](semantics.md), and brackets name the rule that enforces a line (`scripts/check-schema.py rules`). Every name is English: titles, labels, slugs (`Defining`, not `정하기`). Only `why`, `text`, `does`, `expects` and `description`, the sentences a person reads, follow the request's language. In Korean sentences a term takes its settled Sino-Korean word first (`병합`), else a transliteration with the English beside it (`브랜치(branch)`); node, edge, property and scenario stay in English.

## Domain

### Names

Ids, slugs and type names follow the grammar's patterns [name-pattern]. No two nodes share an id or a label, ignoring case, spaces, `-` and `_`, and no two rules or scenarios share a slug; only an edge's label may recur [unique-names]. No name is an Alloy keyword (`open`, `run`, `in`, `until`, `check`, …) or a translation word (`Now`, `Call`, `happens`, `at`, `self`, `result`) [vocabulary]. Forms by element:

- Scenario: verb phrase with object (`land-change`).
- Rule: a property (`least-privilege`).
- Level: noun phrase for the whole (`Pull request lifecycle`).
- Part: noun phrase.
- Area: noun phrase for who or where (`Squad`).
- Call: present-tense verb, read from → to (`points to`).
- State: adjective or participle (`Merged`).
- Transition: plain verb (`mark ready`).

## Levels

- The document's `level` is the root, the system's outermost repeating structure; a node opens the level inside it with `opens`.
- Keep 2 to 7 nodes on a level; group what reacts alike and detail it below.
- An edge that crosses a boundary ends on the opener, on the outer level [edge-across-levels].
- A statechart names its `subject`, the one thing whose states these are, and `initial`, one state per region [four-states].
- Give a state's event only where the state has that edge; a transition stays in its region, every state is reached, and no two states react alike [four-states].
- Name a transition's `changes` as `Type.attr` for every attribute it may change.

**Attributes and calls.** Parts carry `attrs` as `name: Type`: `T` one, `T?` at most one, `T[]` any number, `T[1..]` at least one; `A | B` either, `(A, B)[]` pairs. `name: Bool` is a subset of the part (`ships: Bool` makes `Ships`). A call is a field: the attribute that points at its target (name it with `attr` when two could), or else a field named by its verb (`runs on` is `runsOn`) [typed].

**Types.** A type is a part's name without spaces (`Pull request` is `PullRequest`); a name declared in `types` with one sentence, opened by `{a, b}` for a set of literal values; or `Text`, `Url`, `Date`, `Number` or `Count` [typed].

**Regions and syncs.** A state level's `regions` (each state's `region`) are parts of one thing that change state on their own, such as a branch on your machine and on GitHub. Use them instead of multiplying states. They meet only through `syncs`, `{ "name", "when": event, "where": state, "then": event }`, which fires `then` in another region in the step `when` happens, while `where` holds [syncs].

**Areas.** Give `areas` where a reader takes several nodes in as one. An area holds at least two nodes [area-size], and has either more links inside than outside or a `unit`, the name a person uses for it, such as a team or a deploy unit [area-cohesion].

## Scenarios

A Scenario is one independent question the model answers, walked over the nodes that answer it: a use ("When <actor> does X, Y happens") or a claim ("To see why <claim>, …") walked from the claim to what it rests on. A branch or a failure is its own Scenario, and adds what differs to the usual name: `ship-a-bet`, `ship-a-bet-replan`.

A `walk` lists its steps, each `{"place", "does", "expects"}` [steps]:

- `place` is the node where the step happens, or a list of parts of one level used together, each next place one edge from the last.
- A step may go along an edge, into an opened node's level, out of it, or along an edge of the opener; where two edges fit, name one with `"edge": "label"`.
- `does` says what happens; `expects` says what is true afterwards, checkable.

## Rules

A rule is a proposition no other rule implies; Alloy checks once that it holds.

- **Where it sits**: name a rule in the `rules` of the node or edge that holds it. On a transition a `must` is also a guard: the event happens only when it holds.
- **Kind**: `must` (breaking it breaks a result) or `should` (makes things worse).
- **Formulas are Alloy 6** over the module's names [vocabulary]: predicate, relational, integer and temporal (`always`, `eventually`, `after`, `once`, `until`, `;`). Keywords are words: `not`, `and`, `or`, `implies`, `iff`, `else`.
  - `x.attr` is a member, `x.verb` that the event happened now, with no arguments; a state's name is the set of things in it; another rule is a predicate by its lowerCamel name.
  - Values are names, not strings: `review.verdict = approve`. The next state is written with `after`, never a prime.
  - Variables are named like code, never one letter, never a name of the module: `all pr: PullRequest, review: pr.reviews | review.author != pr.author`.

## Metadata

Every node, edge and rule carries `meta` [source-missing, description-missing]:

- `source`: `path:line` or `path:line-line` relative to the repository root, or a url, only for a system known solely from web documents, so no document mixes the two [source-pointer, source-mixed]. `check doc.json --root <repo>` resolves each path [source-unresolved].
- `description`: plain, full sentences, first what it is for, then what follows; never a fragment or a repeat of the label.

A level's `why` says what a reader learns there.

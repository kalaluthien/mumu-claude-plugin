# Plan

Scope and plan a book: interview the owner, record the model in `book.json`, and pass the `plan-check` and `skeleton` gates.

## Domain

### config boundary
Owner values (register, banned forms, naming, what a named style means) enter as config: `book`, `terms`, `forbid` (lint regexes), `decisions`. A named style sets the Minimum node, the explanation shape, the interaction policy and `length`. `init --lang L` sets `book.lang`, which picks `assets/lang/L.json`: the strings inside the prose, the fonts, the language rules lint applies, and the `register.forms` that `book.register` names. Controls stay English unless the owner names them in `book.strings`.

## Steps

### interview

| Node | Records | Grill |
|---|---|---|
| Form | `book.policies.scale` | Is a book right, or a single page, slides, a doc or a tool? Another form leaves this skill |
| Reader and goal | `book.reader`, `book.goal` | What can the reader do at the end that they cannot now? |
| Emphasis | `book.emphasis`: what the reader must do beyond knowing, such as applying a rule to a new case or recognising the real thing | What can only the book give that a lookup cannot? |
| Core questions | `questions`, after researching the field's standard problems | Which question would an expert add or cut? Where does the frame break? |
| Minimum | the few named ideas of the map and their dependency order | Which idea could go without losing a question? |
| Running case | `project` facts as short noun phrases, including the case's world; `canon` for every constant several units repeat, fixed before writing | Does every unit see the same candidates, numbers and names? |
| Sources | `sources`: each piece of source material a card reads, with the unit that teaches it | Could a newcomer fetch every input a card hands them? |
| Patterns | `new_patterns`: `[{id, family, why, elements, new_elements?, nearest, differs, units}]`; `agents plan` sends a pattern scout, which proposes candidates | What does a practitioner in this field do or see that no catalog pattern (`pattern list`) makes the reader do? |
| Tasks | where manipulation tasks fit; `custom` widgets in `book.js` | What does a practitioner make or operate, and can a page check it? |
| Terms | concept forms as practitioners say them, checked against localized docs; rivals and forced translations to `avoid`; `terms` for recurring role words | Which word is a forced translation or collides with a term? |
| Requirements | round 1 directives, one per `note --topic` | How many figures, exhibits and cards per unit? Which models need the full shape? Where do terms boxes go? |
| Acceptance | policies, `lexicon`, `homes`, `title`, `doc_title` | How will the user judge it done? |

### new-patterns
The one place for a book pattern's life; SKILL.md and the other references point here.

| Step | Rule |
|---|---|
| Scout | `agents plan` emits a `b-pattern-scout` task (research-bulk; skipped when `new_patterns` is 0 by user decision): it runs `pattern list`, compares the catalog with what practitioners of the book's field do or see, and proposes at least 2 problem and 1 visual candidate, each with `nearest` and `differs` |
| Plan | `book.policies.new_patterns` is the count wanted per family. `0` counts only with a `decisions` entry `{node: "policies.new_patterns", chosen: 0, how: "user"}`; without it B5 is an error. `differs` is the move the pattern forces that `nearest` cannot. `local: REASON` keeps one out of promotion. The skeleton gate refuses a list that is short, reuses a catalog id, names an unknown element or leaves `nearest` or `differs` empty |
| Use | A card labels its pattern in `slots/`; a figure carries `data-pattern` on the figure or its svg, or `Fig(..., pattern='id')` in its script. Cards and figures count alike, in the brief's spread and the review gate's 2-use rule |
| Document | `BOOK/catalog/patterns/ID.md` with Why it works, Parts, Examples, Compose and vary, Seed, as in the skill's catalog; a new element is `BOOK/catalog/elements/ID.json`, and a new check on it is code in `BOOK/catalog/checks/ID.py` defining `check(spec, i, ctx)`, with its `breaks` in the element JSON |
| Review gate | Refuses a new pattern with fewer than 2 labelled uses (cards and figures), without its `.md`, or with a new element whose checks fail |
| Promote | `pattern promote ID --dir BOOK [--as-variant-of P]` validates the element JSON (clean errors), copies a new check into the skill's pcheck, and refuses with the reason when the check misses its `breaks`, the element set equals a catalog pattern's, or book nouns appear outside Examples. The pattern's Seed lands in its `.md` and in `assets/seeds.md` as a `card-pattern` row, except a variant's seed identical to its parent's |
| Publish | `approve publish` warns while a book pattern is neither promoted nor `local` |

## Rules

- **Interview**: Use `AskUserQuestion`, at most three rounds before the skeleton, recommended option first, naming its weakest point and a counterproposal. Never ask what can be looked up; `agents plan` sends lookups to research agents. When two answers conflict, ask the conflict as one question.

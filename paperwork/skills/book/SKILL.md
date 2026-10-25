---
name: book-authoring
description: "Use when writing, rewriting or editing an explanatory HTML book or page. Not for tools or slides."
---

## Stages
Every unit and concept answers a core question from the reader's goal. `book.json` is the single source: edit the model or a unit, never the build. The core ends at the `review` gate with a self-contained `book.html`; publishing is a separate stage.

| Stage | Work | Gate (`approve GATE --by user\|self`) | Back-edge |
|---|---|---|---|
| Scope | Interview and config (`reference/plan.md`); `init DIR [--lang L]` | — | — |
| Plan | Model; round 1 via `note --topic`; `agents plan` (`reference/plan.md`) | `plan-check`: `check` clean. `skeleton`: outline-review lens, user approval | Scope |
| Write | Figure scripts, then units (`agents write`; `reference/write.md`) | each `lint --unit` clean | Plan |
| Review | `lint`, `render`, `agents review`, `agents test`, `agents fix` (`reference/review.md`) | `review`: no lint errors, warns fixed or in `decisions`, render ok, every lens `no` fixed or accepted by the user, every book pattern through the lifecycle in `reference/plan.md#new-patterns` | Write or Plan |
| Publish | `reference/publish.md`: an adapter puts `book.html` on a host and records it | `publish`: an approved `review` gate at the current plan hash, lint with 0 errors, and a record in `publish.json` that matches the current build | Review |

A rewrite enters at Scope with `stats OLD.html`; an edit enters at Write with `brief UNIT --revise`. At each gate, show the user what changed, lint counts and open lens `no` rows, then ask; with no user available, take the recommended option, log it in `decisions`, approve `--by self`.

## Roles
Every agent writes only in `.work/AGENT_ID/` and its own files, puts a round's edits in one `edit --patch` file, aims at 40 tool calls or fewer (past that it stops and hands back what is left) and hands back at most 10 lines in the brief's form. A direction arriving mid-run waits for the next round via `note`. Review runs one agent per lens and slice batch; a reviewer's `no` rows also go to `.work/AGENT_ID/no.tsv` (unit, block id, row, fix). `agents STAGE` prints each task's model, effort and batch; `book.policies.models` (`{role: {model, effort}}`) overrides them. Every command takes the book as `DIR` or `--dir` (`agents STAGE [DIR]`: DIR before or after STAGE, or `--dir`); a lint line names the file to read after "read". Units and blocks are addressed as `UNIT` and `#id` (`show UNIT '#id'`, `edit`, `shot --sel '#id'`).

| Role | Job | Runs |
|---|---|---|
| lead | stages, gates, rounds | `agents STAGE`, `note`, `round show\|close`, `approve`, `check`, `lint`, `render [--quick]`, `build`, `rules`, `stats` |
| research-bulk, research-explore | source and term checks in parallel; open questions with graded sources; the plan stage's pattern scout | `brief --research Q [--bulk]`, then what it lists |
| sources, fixer | fix rounds from lint findings, lens `no.tsv` rows and render findings: study-note fields (haiku), other edits (sonnet) | `agents fix [--units IDS] [--render FILE]`, then each `brief --fix RULES --units U`; no hand-written briefs |
| writer | one unit | `brief UNIT [--revise]`, then what it lists |
| writer (catalog) | cards and figures from elements | `pattern list`, `pattern show P`, `element show E`, `card new` / `fig new`, `card lift U ID` |
| demo | `book.js` demos requested with `note --topic demo` | `brief --demo NAME` |
| review-facts, review-conformance, review-intent, review-coherence | fact tracing; criteria and exceptions; fit to intent; cross-unit (one task per part) | `brief --lens NAME --units U[:N]`, then what it lists |
| test, debug | render, lint and driven shots; a failing behaviour | `brief UNIT --test WHAT`, `brief UNIT --debug SYMPTOM`; fix loop: `render` → `outline`/`show` → `edit --patch` → `shot --sel '#id'` |
| skill editor | the skill itself | `mutate` |

## Gotchas
| Trigger | Breaks | Do |
|---|---|---|
| Renaming a term | Old forms survive in figures and TeX | Add the old form to `avoid` first |
| Reading HTML to check rendering | Context fills | Open only flagged shots or `--sheet` |
| A book language with no `lang/<code>.json` | English rules judge the prose; labels stay English | Add the pack (copy `lang/en.json`) before writing |

## How to Fix
Every lesson except an owner's value lands with a detector seen to catch it first.

| Lesson | Lands in | Detector |
|---|---|---|
| Output feedback that would recur in other books | the skill too, by a row below | as below |
| Format or script can see it | schema, template, build or lint | a `mutate` case |
| Language rule or string | `lang/<code>.json` | a case in the pack's `mutate` list |
| Only a reader sees it | a row in `reference/review.md` or `write.md` | a seed in `tests/seeds.md` |
| Owner value | memory or `book.json` | none: it is the owner's |
| A pattern or element the book developed | `pattern promote` (lifecycle: `reference/plan.md#new-patterns`) | the element checks in `mutate`; the pattern's Seed |

A big change is planned, attacked and filtered, then shown as at most five non-conflicting proposals approved one at a time; a structure-critique pass looks for merges and cuts. Pilot it on a slice of an existing book. Write the skill files only after the user approves.

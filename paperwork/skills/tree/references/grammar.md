# Grammar

Four concepts: Part, Decision, Option, Answer. A plan is `{"title": str, "files": int, "parts": [Part]}`, `files` optional.

## Shapes

| concept | keys |
| --- | --- |
| Part | `text` (required), `kind`, `source`, `parts`; with `pick` and optional `else` it is a Decision, which may hold `name` and `requires` |
| Option | `text` (required), `parts` (Parts with no `pick` or `else`), `name`, `requires`, `excludes`, `files` |

- `kind` is a lowercase word: `goal`, `step`, `evidence`, `risk`, `note`, `consequence`, `question`, `mockup`. `quote` and `diff` join them. `risk` is drawn with a Risk pill; `mockup` draws its text as a screen in a frame, monospace, `[[x]]` a primary button and `[x]` a button; `quote` draws its text with its `source`; `diff` colours each line by its first character, as `gh pr diff` does. An exhibit is plain text of the plan, never computed or checked. Kinds are free; only these four have a look.
- `source` is a link a person can open (`https://` or `http://`, not `localhost`), or `<person>, YYYY-MM-DD`: who said it and the day. A path, an internal id, a tool or an agent name is not a source. `evidence` and `quote` always have one; a claim with none is dropped or written as `guess`, its text starting `Guess:`. The person form has no middle dot, since the page draws the source as written.
- `pick` is one object, so a Decision holds exactly one pick. A repeated key is refused when the file loads.
- `files` on the plan and on an Option is a whole number, the writer's estimate; the page adds those in force and marks the sum as an estimate.
- An Option's `parts` are shown before the choice. They have no ids and take no strike, comment or edit.

## Relations

A Decision or an Option has a `name`, lowercase letters, digits and `-`, only when a relation names it. A relation is `<decision>.<option>`.

| key | on | holds when | else |
| --- | --- | --- | --- |
| `requires` | Decision | every named option is in force | the Decision is not needed, and writes no line |
| `requires` | Option | every named option is in force | the option is blocked |
| `excludes` | Option | no named option is in force | the option is blocked |

A relation names only an earlier Decision, so a cycle cannot be written and the graph is read in one pass, top to bottom. A follow-up is a later Decision with `requires`. The option in force of a Decision is its answer while that holds, else its `pick`, else its first open option. An Other answer satisfies no relation. A Decision with one option left of several, and no answer, is settled: it folds, and the next plan holds that option as its `pick`.

## Ids

An id is a position over `parts` only: depth-first, 1-based, dot-joined (`1`, `1.2`, `1.2.1`). Never write one; an `id` key is an unknown key. Options are numbered as pressed: `pick` is 1, then `else` in order. The free-text Other is the last number and is not written.

## Rules

A refusal prints `path: rule: detail`.

| rule | refuses |
| --- | --- |
| `duplicate-key` | a key written twice in one object, such as two `pick` keys |
| `unknown-key` | a key the grammar lacks at that place, such as `id` or `then` |
| `else-needs-pick` | `else` with no `pick` |
| `decision-in-option` | `pick` or `else` inside an Option's `parts` |
| `empty-text` | an empty or missing `text` or `title` |
| `unreadable-source` | a `source` that is neither a link a person can open nor `<person>, YYYY-MM-DD` |
| `evidence-needs-source` | a Part of kind `evidence` with no `source` |
| `quote-needs-source` | a Part of kind `quote` with no `source` |
| `bad-name` | a `name` that is not lowercase letters, digits and `-` |
| `duplicate-name` | a Decision's name, or an option's within its Decision, written twice |
| `forward-ref` | a relation that names a Decision not before this one |
| `unknown-ref` | a relation that names no Decision, or no option of it |
| `default-blocked` | a `pick` blocked when every pick stands, so the default path cannot hold |
| `dead-end` | answers that leave a needed Decision with no open option |
| `unused-name` | a `name` no relation uses |
| `bad-kind` | a `kind` that is not lowercase letters and `-` |
| `wrong-type` | a value of the wrong JSON type |
| `missing-key` | a plan with no `parts` |
| `bad-json` | text that is not JSON |

The refused fixtures in [../fixtures/refused/](../fixtures/refused/) show the refusals. `answer-plan.json` is a valid plan, and its four `*.answer.md` are refused by the reader, not the checker: `read-answer.py --expect-refused fixtures/refused/answer-plan.json fixtures/refused/*.answer.md` prints `refused 4 of 4`.

## Answer

One Markdown form, one line per Part touched, nothing for a Part kept. A pressed `pick` writes its line even for option 1, so a missing line means unanswered, not agreed:

```
# Answer: <title> · plan <stamp>
- 2 pick 2
- 2 other: <text>
- 3 struck: <reason>
- 4 comment: <text>
- 5 edited: <new text>
```

The stamp is the first eight hex digits of the SHA-256 of the plan's JSON with sorted keys and no spaces; `make-page.py` writes it into the page. An Answer whose title or stamp differs from the plan it is read against is refused, since ids are positions and an older version's ids name other Parts; `stale.answer.md` shows it.

A Part may have several lines, such as a pick and a comment, but one pick or other at most. The reader refuses with the line number: an unknown id, a `pick` out of range, a `pick` of a blocked option or of a Decision not needed, a strike of a Part another Decision depends on, `pick` on a Part with no options, or a line it cannot parse.

## Apply

`read-answer.py` applies every line against the ids of the plan the Answer was made from, then removes struck Parts last.

- `pick N`: Option N becomes the `pick`; the others follow in `else` in their old order. A Decision that an answer settled, or whose `pick` it blocked, takes its option in force the same way.
- `other`: a new pick `{"text": ...}`; the old options move to `else`.
- `struck`: removes the Part and its subtree.
- `comment`: appends a child Part `{"kind": "comment", "text": ...}`.
- `edited`: replaces `text`.

The next plan must pass the checker, or the reader refuses. On stderr the reader prints `not answered: <id> <text>` for each Decision left open.

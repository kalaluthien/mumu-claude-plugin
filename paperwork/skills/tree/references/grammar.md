# Grammar

Four concepts: Part, Decision, Option, Answer. A plan is `{"title": str, "parts": [Part]}`.

## Shapes

| concept | keys |
| --- | --- |
| Part | `text` (required), `kind`, `source`, `parts`; with `pick` and optional `else` it is a Decision |
| Option | `text` (required), `parts` (Parts with no `pick` or `else`), `then` |
| follow-up Question | `text`, `pick`, `else`; its options are Leaves: `text`, `parts` |

- `kind` is a lowercase word: `goal`, `step`, `evidence`, `risk`, `note`, `consequence`, `question`, `mockup`. `risk` is drawn with a Risk pill; `mockup` draws its text as a screen in a frame, monospace, `[[x]]` a primary button and `[x]` a button. Kinds are free; only these two have a look.
- `pick` is one object, so a Decision holds exactly one pick. A repeated key is refused when the file loads.
- A Leaf has no `then`, so a follow-up inside a follow-up cannot be written.
- An Option's `parts` are shown before the choice. They have no ids and take no strike, comment or edit.

## Ids

An id is a position over `parts` only: depth-first, 1-based, dot-joined (`1`, `1.2`, `1.2.1`). Never write one; an `id` key is an unknown key. Options are numbered as pressed: `pick` is 1, then `else` in order. The free-text Other is the last number and is not written.

## Rules

A refusal prints `path: rule: detail`.

| rule | refuses |
| --- | --- |
| `duplicate-key` | a key written twice in one object, such as two `pick` keys |
| `unknown-key` | a key the grammar lacks at that place, such as `id`, or `then` inside a follow-up |
| `else-needs-pick` | `else` with no `pick` |
| `pick-missing` | a follow-up Question with no `pick` |
| `decision-in-option` | `pick` or `else` inside an Option's `parts` |
| `empty-text` | an empty or missing `text` or `title` |
| `bad-kind` | a `kind` that is not lowercase letters and `-` |
| `wrong-type` | a value of the wrong JSON type |
| `missing-key` | a plan with no `parts` |
| `bad-json` | text that is not JSON |

The refused fixtures in [../fixtures/refused/](../fixtures/refused/) show each of the four shape refusals. `answer-plan.json` is a valid plan, and `unknown-id.answer.md` names a Part it lacks; the reader refuses that, not the checker. `read-answer.py --expect-refused fixtures/refused/answer-plan.json fixtures/refused/*.answer.md` prints `refused 2 of 2`.

## Answer

One Markdown form, one line per Part touched, nothing for a Part kept:

```
# Answer: <title> · plan <stamp>
- 2 pick 2
- 2 pick 1 then 2
- 2 other: <text>
- 3 struck: <reason>
- 4 comment: <text>
- 5 edited: <new text>
```

The stamp is the first eight hex digits of the SHA-256 of the plan's JSON with sorted keys and no spaces; `make-page.py` writes it into the page. An Answer whose title or stamp differs from the plan it is read against is refused, since ids are positions and an older version's ids name other Parts; `stale.answer.md` shows it.

A Part may have several lines, such as a pick and a comment, but one pick or other at most. The reader refuses with the line number: an unknown id, a `pick` out of range, `then` on an Option with no follow-up, `pick` on a Part with no options, or a line it cannot parse.

## Apply

`read-answer.py` applies every line against the ids of the plan the Answer was made from, then removes struck Parts last.

- `pick N`: Option N becomes the `pick`; the others follow in `else` in their old order. `then M` does the same inside that Option's follow-up.
- `other`: a new pick `{"text": ...}`; the old options move to `else`.
- `struck`: removes the Part and its subtree.
- `comment`: appends a child Part `{"kind": "comment", "text": ...}`.
- `edited`: replaces `text`.

The next plan must pass the checker, or the reader refuses.

---
name: grill-me
description: Use when the answer is still the user's to make - a decision, a proposal or a plan with open choices to settle by asking them; not when the facts settle it or code is under review.
disable-model-invocation: true
---

# grill-me

Interview the user relentlessly until you reach a shared understanding. Map
this as a **design tree**: every decision branches into the decisions that hang
off it.

Work the tree in **rounds**. The **frontier** is every decision whose
prerequisites are already settled. A question whose answer depends on another
question still open in this round belongs to a later round.

## Asking a round

- Every round is one `AskUserQuestion` call of at most four questions, and
  nothing else: no numbered text, no pasted-back block. Then wait.
- Pick the four from the frontier by impact first - the answer that changes
  the most of the tree - then by conceptual order, a concept before the
  choices built on it. The rest of the frontier waits.
- Choose each next round from the answers so far: recompute the frontier,
  drop questions an answer made moot, and ask the next four the same way.
- Before each round after the first, write one line of what the last round
  settled, wholly in the user's language, its label included (`Settled: …`,
  `정한 것: …`).
- A free-text answer is not settled as typed: restate it as a concrete
  proposal in the next round ("I read your last answer as: …") and settle it
  when the user confirms that.
- An objection to a settled answer - yours, after attacking it once with a
  counterexample, an edge case or a check that can fail - is its own question
  in the next round, its header tagged `[objection]` in the user's language.
- An answer that is itself a question is answered with facts in the next
  round, and never recorded as a decision.
- Word each question so "yes" accepts the recommended option.
- Facts come from `drill-it`, never from the user: before each round, run
  the `drill-it` skill with the purpose `decision`, the round's open decisions
  and Question shape below, and ask only from what it hands back.

## Question shape

Each question is answerable without opening a file. Its body carries:

- the current state, quoted with its `path:line`;
- why it matters: the failure the choice causes or prevents, with a real case
  where one exists.

Each option's description names its cost as a number and its downside. The recommended option is the first, labelled `(Recommended)`, its answer as
bullets.

## Settling

Done when every branch of the tree is visited, nothing silently assumed, and
the user confirms a summary of the settled answers. Act on nothing before that.

## Output

The settled answers only: each decision and its answer, no transcript of the
rounds.

The answer goes to chat by default, and into a document as well when one is
asked for. When the output is not a markdown document, end with one line
asking the user to run `/paperwork:show-me` on the settled answers.

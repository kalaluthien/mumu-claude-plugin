# Review

Check a written book by lint, render and one reviewer per lens, then fix rounds, up to the `review` gate.

## Domain

A lens is one reviewer's question: its role, gate and inputs, then rows answered yes or no per unit. `agents review` sends one task per lens and slice batch, built from the `### lens:` sections under Rules and the `### protocol` under Steps.

## Steps

### protocol
Answer each row yes or no per unit from the inputs only; a no quotes its place and gives a repair in the book's language. A row that points to `write.md#id` tests that row. Hand back in the brief's form, and write each `no` as a line of `.work/AGENT_ID/no.tsv`: unit, block id, row id, repair (tab-separated).

Fix rounds go through `agents fix [--render FILE]`, which reads lint findings, render findings (`.work/render.json` or `.txt`) and reviewers' `.work/r-*/no.tsv` rows (rule `no:ROW`) and renames a processed file to `no.done.tsv`; not hand-written briefs; `agents fix` prints each task's role, model and batch. B* and G1 findings go to the lead.

## Rules

### lens: outline-review
Role `review-coherence`, at the `skeleton` gate. Inputs: `book.json`, `check`.

| id | yes when |
|---|---|
| lens-outline-questions | A skeptical expert finds the questions core and following from the goal; no: baking without fermentation |
| lens-outline-frame | The frame says where it breaks; each model names its assumptions; no: "all is supply and demand" |
| lens-outline-facts | Each core unit makes a fact a later decision uses; no: an unused made fact |
| lens-outline-scent | Each unit title predicts its content to a reader scanning the contents; no: "Basics", "More on X" |
| lens-outline-type | What the reader looks up again (tables, parameters, procedures) has a reference home: terms box, appendix or home figure; no: parameters only mid-paragraph |

### lens: editor
Role `review-conformance`. Inputs: `text --unit U --only prose`.

| id | yes when |
|---|---|
| lens-editor-native | write.md#sent-native holds, spliced facts included; no: "it is by this book called x" |
| lens-editor-terms | One field word per concept, no forced coinage; a found pair goes into `terms[].avoid` so lint enforces it; no: "rate" and "speed" for one quantity |

### lens: shape
Role `review-intent`. Inputs: `text --unit U --only stems`.

| id | yes when |
|---|---|
| lens-shape-concept | Each core concept and model has question, case, attempt, frames, key sentence, real why, limit; no: four forces listed and summed |
| lens-shape-terms-box | write.md#shape-terms-box holds, before first use; no: three chord names defined inline |
| lens-shape-practice | An example models one step, then hands over; each gist says where the unit sits; no: no worked step |

### lens: items
Role `review-conformance`. Inputs: `cards --units IDS --out S/cards.json`, `cards --units IDS --out S/cards.json --score S/picks.json`, `text --unit U --only cards`.
Solve `cards.json` blind first, writing `picks.json` as `{id: {"pick": letter, "cue": "knowledge|cue|guess"}}`; then score; then read the cards text.

| id | yes when |
|---|---|
| lens-items-blind | Cues solve at most 20% of a unit's sets; no: one sane option beside strawmen |
| lens-items-unique | write.md#card-unique holds and no wrong option's why concedes; no: two equally good questions |
| lens-items-pattern | write.md#card-pattern holds for each labelled card (`pattern show P`, then its label and rival lines in the cards text); no: rivals whose right_when all say "in another situation" |
| lens-items-level | write.md#card-level holds; no: an apply card echoing the line above |

### lens: reader
Role `review-intent`. Inputs: `text --unit U --only stems`, `text --unit U --only figs`, `shot U --solve --sheet --quick --out S/shots`.
Open flagged shots, the sheet and `plot`/`multiples` shots.

| id | yes when |
|---|---|
| lens-reader-source | write.md#shape-source holds for every card input; no: log lines before the log is shown |
| lens-reader-path | write.md#fig-draw-path holds; no: five stations in a paragraph |
| lens-reader-exhibit | write.md#card-exhibit holds; no: 80 words describing a chart |
| lens-reader-chart | write.md#fig-channel, #fig-scale, #fig-label and #fig-uncertainty hold in each `plot` or `multiples` shot; no: a bar axis starting at 90 |
| lens-reader-alt | write.md#fig-alt holds for each figure in the figs text; no: alt "A chart" or "Diagram of the process" |
| lens-reader-flow | On a phone the next action is clear and nothing needed is folded; no: a continuous value set by taps |

### lens: facts
Role `review-facts`. Inputs: `text --unit U --only claims`.
Redo each worked example before judging it.

| id | yes when |
|---|---|
| lens-facts-correct | Claims, numbers, worked examples and timelines are right; no: a reading logged before the heater was switched on |
| lens-facts-short-path | An absolute (only, never, first, none) survives a search for a counterexample or second path; no: repeated subtraction also finds the greatest common divisor |
| lens-facts-cited | Each `data-cite` sentence says what the located passage supports; no: the study measured recall, the sentence says comprehension |
| lens-facts-strength | Claims at their grade from primary sources, numbers with sample size; no: 8 people called proof |
| lens-facts-model | Each model states what it assumes and ignores, in the field's term; no: "weight" for mass |

### lens: coherence
Role `review-coherence`, one task per part (not sliced). Inputs: `text --unit U --only claims`.

| id | yes when |
|---|---|
| lens-coherence-case | Units share the case's names, numbers and their written format; no: 8 items, then 10; 1,200 then 1200 |
| lens-coherence-names | A defined category name means one thing in a unit; no: a 2×2 cell named like one of its axis values |

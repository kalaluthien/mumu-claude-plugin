# View writing

`view.json` (`assets/view-schema.json`) says how to draw a Schema document, never changing it (fixes go to the document). Brackets name the enforcing check (`make-diagram.py rules`). `make-diagram.py new view.json` starts one; `next` is the reader's next step; `why` says why each changed `plan` default changed [form].

## Views

Name the diagrams this domain's practitioner expects first (ER model). Draw each by a level, `{"name", "level"}`, or omit it, `{"name", "why"}` [form]. A view no level draws needs a level opened, or a reason.

- newcomer: `depth: overview`; audit one part: `deep` it, `shallow` the rest

## Depth

**Depth.** `depth` picks which levels the views feature; the page keeps all [depth]. `overview`: root and one level; `working` (default): the levels below; `detailed`: also every operation as one action. At `working`, feature a node's inside when either holds:
- **A Scenario or a rule lives inside**: A Scenario needs it, or a `must` rule is kept there.
- **A design decision lives inside**: It is hard or likely to change and sets what the system can do (Parnas).

Feature no deeper when either holds:
- **Only what the intent can ignore is left**: It would vanish with perfect technology (McMenamin and Palmer), or is an unchanged library. Caching, failure, distribution and deployment count if the intent asks.
- **Only the cases differ**: Open the most distinctive; list the rest as `facts`.

`deep` opens a node these rules stop at; `shallow` keeps one closed.

## Rules

The page's own words (Facts, Insight, main path, optional), each `facts` item's opening term, each medium and screen `title` and each block `name` stay English (`Defining`, not `정하기`) [names]. Top-level `lang` is the reader's language (`ko`); default `en`.

In a Korean model, `[prose]` (lint) quotes the sentence at fault:
- end in `-니다` or `-니까`, never `-요` or plain `-다`; quotes exempt;
- the particle after an English term follows its last sound (`Alloy가`, `run이`), with no space; `수 있`, `수 없` apart;
- no `위`, `아래`, `앞` or `다음` before `그림`, `표`, `식`, `그래프` or `칸`; name the figure (`그림의 위 칸` is fine).

## Layout

Without `x` and `y` the engine places nodes itself. Set them when a place means something or `fits` fails (root first): neighbours share a row or column, a busy node is central. A diagonal edge needs one empty corner. A long edge down a column runs on its right; `via: "left"` when busy. On a phone the root has 1-2 columns, text at 9 px (`assets/phone-limits.json`); no two root partitions join at more than 3 pairs of nodes [phone], and the root fits its card [fits].

## Screens

Mock each screen people use in `screens`; give `ui: {screen, block}` to every node it shows (part, state, or activity whose result appears on it); its note shows that block, on every level. Build the mock from source:
- Read the code that draws the screen; take its regions, order and visible text verbatim.
- Keep the real layout and block type (`tabs`, `list`, `button`, …).
- With no code, use screenshots or documentation; a guess is `invented: true`.

## Show

`show` turns off `formulas`, `replay` or `media`. `max_nodes` (7): most nodes per level [size].

`facts` hold the system's own facts (names, counts, paths, limits, sources), never the plan (question, views, depth, proof scope, base commit), which goes to the chat hand-over [facts].

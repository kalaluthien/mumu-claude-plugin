# View writing

`view.json` (`assets/view-schema.json`) says how to draw a drill-it
`system.json` (diagrams, depth, language, places, screens), never changing it
(fixes go to drill-it). Brackets name the enforcing check
(`make-diagram.py rules`). `make-diagram.py new view.json` starts one; `next`
is one sentence on what the reader does next, `why` says why each changed
`plan` default changed [form].

## Views

Name the diagrams this domain's practitioner looks for first (ER model, backend). Draw each by a level, `{"name", "level"}`, or omit it, `{"name", "why"}` [form]. A view no level can draw needs a level opened, or a reason.

| Intent | Typical plan |
|---|---|
| explain the system to a newcomer | `depth: overview` |
| audit one part | `deep` that part, `shallow` the rest |

## Depth

**Depth.** `depth` picks which levels the views feature; the page keeps all [depth]. `overview`: root and one level; `working` (default): the levels below;
`detailed`: also every operation as one action. At `working`, feature a node's
inside when either holds:
- **A Scenario or a rule lives inside.** Following a Scenario needs it, or a `must` rule is kept there.
- **A design decision lives inside.** It is hard or likely to change and sets
  what the system can do (Parnas). Machinery many cases
  share is drawn once.

Feature no deeper when either holds:
- **Only what the intent can ignore is left.** It would vanish with perfect
  technology (McMenamin and Palmer: infinite speed, nothing fails),
  or is an unchanged library, and the intent ignores it. Caching, failure, distribution
  and deployment count when the intent asks.
- **Only the cases differ.** Open the most distinctive; list the rest as `facts`.

`deep` opens a node these rules would stop at; `shallow` keeps one closed.

## Language

The page's own words (Facts, Insight, main path, optional), the term opening
each `facts` item, each medium and screen `title` and each block `name` stay
English (`Defining`, not `정하기`) [names]. Set top-level `lang` to the reader's
language (`ko`); default `en`.

In a Korean model, `[prose]` (lint) quotes the sentence at fault:
- register: end in `-니다` or `-니까`, never `-요` or plain `-다`; quotes exempt;
- the particle after an English term follows its last sound (`Alloy가`, `run이`), with no space; `수 있`, `수 없` apart;
- no `위`, `아래`, `앞` or `다음` before `그림`, `표`, `식`, `그래프` or `칸`; name the figure (`그림의 위 칸` is fine).

## Layout

Without `x` and `y` the engine places each node beside a placed neighbour,
crossing the fewest nodes. Set them when a place means something or `fits`
fails (root first): a small grid, neighbours sharing a row or column, a busy node central. A diagonal edge needs one empty corner. A
long edge down a column runs on its right; `via: "left"` when that is busy.
On a phone the root is laid out in 1-2 columns, text at 9 px
(`assets/phone-limits.json`); no two root partitions join at more than 3 pairs
of nodes [phone], and the root fits its card [fits].

## Screens

When people use the system through a screen, mock it in `screens` and give
`ui: {screen, block}` to every node it shows (a part, a state, or an activity
whose result appears on it); its note shows that block, on every level.

Build the mock from source, not memory:
- Read the code that draws the screen; take its regions, order and visible text
  verbatim (labels, menu items, empty states).
- Keep the real layout (order, scrolling, primary control) and the block type
  the code renders (`tabs`, `list`, `button`, `choices`, …).
- With no code, use screenshots or documentation; a guess is made up (`invented: true`).

## Show

`show` turns off `formulas`, `replay` or `media`. `max_nodes` (7): most nodes
per level [size].

`facts` hold the system's own facts (names, counts, paths, limits, sources), never the plan (question, views, depth, proof scope, base commit): that goes to
the chat hand-over [facts].

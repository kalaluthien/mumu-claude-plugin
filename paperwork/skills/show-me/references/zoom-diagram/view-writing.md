# View writing

A view file (`view.json`, fields in `assets/view-schema.json`) says how to draw
a system model that drill-it wrote (`system.json`): which diagrams, how deep,
in which language, where nodes sit and which screens they show. It never
changes the system: a fix to what the system is goes to drill-it. Brackets name
the drawing check that enforces a line (`make-diagram.py rules`).

`make-diagram.py new view.json` starts one; `next` says in one sentence what the
reader does after reading [form]. The view's `plan` holds the drawing's
parameters; say in `why` why each changed default was changed [form].

## Views

Name the diagrams someone who works in this domain would look for
first: an ER model and the API for a backend, page navigation for a front end,
a CONSORT flow for a trial, the method and the claims for a paper. Each is
drawn by a level, `{"name", "level"}`, or left out with a reason,
`{"name", "why"}` [form]. A view no level can draw is a level you have not yet
opened, or a reason to give.

| Intent | Typical plan |
|---|---|
| explain the system to a newcomer | `depth: overview` |
| audit one part | `deep` that part, `shallow` the rest |

## Depth

**Depth.** The page keeps every level the model holds; `depth` only picks
which levels the views feature, and the reader stops where they like [depth].
`overview` features the root and one level, `working` (default) the levels
below, `detailed` also every operation as one action someone can do or point
to. At `working`, feature a node's inside when either holds:
- **A Scenario or a rule lives inside.** The reader needs its inside to follow
  a Scenario, or a `must` rule is kept there.
- **A design decision lives inside.** It is hard or likely to change and sets
  what the system can do (Parnas), so an insight could be written about it.
  Machinery many cases share is drawn once.

Feature no deeper when either holds:
- **Only what the intent can ignore is left.** It would vanish with perfect
  technology (McMenamin and Palmer: infinite memory and speed, nothing
  fails), or it is a library used unchanged, and the intent is not about it.
  Caching, failure, distribution and deployment are the system when the
  intent asks about them.
- **Only the cases differ.** Open the most distinctive case and list the rest
  as `facts`.

`deep` opens a node these rules would stop at, and `shallow` keeps a node closed.

## Language

The page's own words (Facts, Insight, main path, optional), the term that opens
each `facts` item, each medium's `title` and each screen's `title` and block
`name` are English as well (`Defining`, not `정하기`) [names].
Set the top-level `lang` to the reader's language (`ko`); the page declares it
for fonts and line breaks, and it is `en` by default.

- In a Korean model, `[prose]` (lint) reads every description and quotes the sentence at fault:
  - the register: end a sentence in `-니다` or `-니까`, never `-요` or a plain `-다`; a quote is exempt;
  - the particle after an English term follows its last sound (`Alloy가`, `run이`);
  - the spacing: no space between a term and its particle (`Alloy가`), and `수 있`, `수 없` apart;
  - the position word: no `위`, `아래`, `앞` or `다음` before `그림`, `표`, `식`, `그래프` or `칸`; name the figure (`그림의 위 칸` is fine).

## Layout

Leave `x` and `y` out and the engine places each node beside a placed
neighbour, where its edges cross the fewest nodes and partitions stay blocks.
Set them when a place means something or when `fits` fails (the root first): a small grid where neighbours share a row or column, a busy
node goes in the middle, and two or three columns is usual. An edge between diagonal cells needs one empty corner.
A long edge down a column runs on its right; give it `via: "left"` when the
right is busy.
On a phone the engine lays the root out again in two columns or one, with
long labels on two lines and text at 9 px (limits in `assets/phone-limits.json`);
no two of the root's partitions join at more than 3 pairs of nodes [phone],
and the root never needs more than its card [fits].

## Screens

When people use the system through a screen, mock that screen in `screens`
and give `ui: {screen, block}` to every node the screen shows: a part of it, a
state it is in, or an activity whose result appears on it. Its
note then shows the screen with that block picked out, on every level.

A mock predicts what the real screen looks like, so build it from the source,
not from memory of similar apps:
- Read the code that draws the screen (templates, components, styles,
  resource and string files) and take its regions, their order, and its
  visible text verbatim: titles, button labels, menu items, empty states.
- Keep the real layout: what sits beside what, what scrolls, which control is
  primary. Pick the block type that the code renders (`tabs`, `list`,
  `button`, `choices`, …).
- With no code, use the product's screenshots or documentation; a screen you
  had to guess is made up (Media).

## Show

`show` turns off what the page draws: `formulas`, `replay` or `media`. `max_nodes` (7)
is the most nodes one level may hold [size].

`facts` hold the system's own facts (names, counts, paths, limits, sources) and never the plan: the question, the views, depth, proof scope and base commit go to the hand-over in chat, not the page [facts].

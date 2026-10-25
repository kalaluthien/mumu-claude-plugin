# Write

## shape
| id | criterion |
|---|---|
| shape-question | A concept opens on a problem the reader already feels, in words the reader already uses, before any name |
| shape-case | One instance the reader can compute or picture without notes carries the explanation |
| shape-attempt | The reader tries the case in a card or task before the idea is revealed |
| shape-key | The key sentence states the general claim and nothing else |
| shape-why | The why is a real reason in the book's own picture that a doubter accepts without authority, not the claim restated |
| shape-limit | A near-miss shows where the idea stops and what breaks |
| shape-grow | A thin explanation grows by cases, steps or a second view, never by repetition |
| shape-model | A model the reader reasons with gets the whole shape, even inside another unit; a named procedure is met on a case before its name |
| shape-terms-box | Each terms-box entry gives the exact definition, the unit and a typical value; the box comes before the first formula or sentence that uses its names |
| shape-gist | The gist names the unit's question, what it takes and makes possible, and its angle |
| shape-example | The worked step says why it is the right move, not only what it does |
| shape-step | The running-case step makes one decision with the unit's idea |
| shape-close | The close restates the unit in words the unit has not used; a review variant brings new rival beliefs |
| shape-source | The block marked for a source says where the material lives, how to open it, and annotates one real entry |
| shape-fold | Nothing the path needs is folded |

## sentences
| id | criterion |
|---|---|
| sent-plain | One idea per sentence, an actor as subject, an active verb, concrete words |
| sent-point | A paragraph's first sentence states its point |
| sent-native | Drafted in the book's language from the claim, never translated; a foreign name keeps one spelling |
| sent-splice | A spliced fact or label reads as part of its sentence; a list fact is named as a group with its items after |
| sent-numbers | At most two numbers per sentence, rounded and compared |
| sent-analogy | An analogy maps the mechanism and says where it stops |

## cards
A card is hand markup or `<!--card ID-->` with an entry in `slots/UNIT.json` (`card new`; `card lift U ID` turns a hand card into one); build renders the entry and refuses a missing, mistyped or TODO slot (P1); element checks run in lint (P2). `pattern show P` gives a pattern's move, examples and how to vary it; pick and combine elements for the idea at hand (`element show E`), any order and repeats allowed, and name what you combined in `label`. A part no element covers goes in a `raw` element.

`card new [DIR] --unit U --after SEL [--kind K] [--elements E,E] [--id ID] [--label L]` places a stub (kinds: ask, probe, task-sort, task-order, task-select, task-estimate, task-custom); `fig new` takes the same plus `--kind fig|frames` and `--tactic T`. `SEL` is `#id` of the block to follow, as in `show UNIT '#id'` and `shot --sel '#id'`.

| id | criterion |
|---|---|
| card-claim | The card observes one idea, and a reader holding it answers right for that reason |
| card-new-case | A card above `understand` uses a case the unit has not worked, never a sequence or classes a paragraph just listed |
| card-rival | Each wrong option is the move a competent person without the idea would make, as concrete as the answer, ending in the move, not a label for its type; the stem never refutes it. Sources: a prior intuition, a first-order answer, a right fact with a wrong reason |
| card-why | A wrong option's why opens on the fact that breaks that belief without stating the answer; every why uses only what the reader was told |
| card-unique | For each wrong option the writer can say when it would be right, and the stem rules that out |
| card-flat | Difficulty sits on the idea: mental numbers, no unrequested arithmetic, no term the unit has not given |
| card-independent | No card's stem, options or why gives away another card's answer |
| card-level | The labelled level and move are the ones the card needs |
| card-intervene | An intervene card changes one part, order, boundary, assumption or input; options are first-order effect, second-order effect, flip condition |
| card-kind | Every card is machine-checkable, never free text; input matches the manipulation: drag what moves, slide what is continuous, tap what is discrete |
| card-probe | The probe uses a newcomer's words; its options are real prior models |
| card-pattern | A card or figure built from catalog elements does the move its pattern's Why names; each rival's `belief`, `right_when` and `ruled_out_by` are specific to it, not boilerplate |
| card-exhibit | What the reader would see (a chart, page, draft or log) is a static exhibit in the card, in each option when options are alternatives; the stem never points at unshown material |

## figures
A figure is a script using `book.Fig` (`help(book.Fig)`) that saves `figs/ID.svg`, placed as `<!--svg ID-->`, or `<!--fig ID-->` from `fig new` with visual elements (steps, axes, panels, kit-tree, pair, graph, demo) and an `alt` element that composes the alt; it gets a stable id. A figure that uses a catalog pattern names it with `data-pattern` on the figure or its svg, or `Fig(..., pattern='id')` in its script; it counts as a use like a labelled card. Reusable exhibit parts are classes listed in a `/* kit: */` block of `book.js`. Shot checks skip text inside `data-expect="clipped"` and contrast on `[disabled]`, `[aria-disabled=true]` or `[data-inactive]` parts.

| id | criterion |
|---|---|
| fig-show-say | The prose before a figure asks what it answers; the figure shows the case; the prose names what was seen and carries what it cites, never only a caption; a caption says what the figure shows, never how it was drawn, and never repeats the prose |
| fig-no-answer | A figure never hands over the answer a card just asked for |
| fig-draw-path | A path, steps or a structure of four or more parts is drawn, not only narrated; a form to read is drawn with its fields named |
| fig-frames | A process redraws the case's own objects on the same geometry, one change per frame |
| fig-alt | The alt names the kind, what it encodes and the point; a plot names chart type, variables and takeaway |
| fig-color | Colour marks only a real distinction; an ordered quantity takes a lightness ramp (sequential, or diverging around a named midpoint) |
| fig-channel | A quantity the reader compares sits on position along a common scale or on length from zero; area, angle and colour only for a rough reading |
| fig-scale | Bars start at zero; small multiples share one scale or say so on each panel; no dual y-axes; a log scale is named in the prose |
| fig-label | Series are labelled where they are drawn; a legend only when direct labels do not fit |
| fig-uncertainty | A plotted estimate shows and names its interval (CI or SE), or shows outcomes as counted dots; a projection says which distances it keeps |
| fig-metaphor | A metaphor only where its structure maps fully; the caption says where it breaks |
| fig-fork | Two confusable concepts get a separating question and two answers |
| fig-data | Values come from a script through `fact()`; a demo changes exactly the variable it claims to show |
| fig-home | An object drawn in several units is a home figure |
| fig-selectable | An unselected selectable diagram already shows the point |

## evidence
| id | criterion |
|---|---|
| ev-claim | A general or causal claim rests on a study at its grade, cited by `data-cite="note-id"` on its sentence, or on a demo (fig-data); an invented scene only illustrates |
| ev-note | Each study has one home note and grade, with fields `p[data-p=design]` (sample size), `found`, `limits`, `source` (URL or DOI, locator, depth read: abstract, section, full text or summary-read); "full text" only when the document text itself was read, a fetch summary is recorded as summary-read, and a grade above the lowest needs full text |
| ev-sample | A number the case uses carries its sample size; a caveat carries into every later use |
| ev-uncertainty | Hedge words follow the cited grade (`book.strings.hedges`, else the language pack); a derived number carries its own error |
| ev-conditions | A measured number names when, where and on what sample or setup it holds |
| ev-badge | Content the author made (synthesis, invented example, computation) carries a badge |

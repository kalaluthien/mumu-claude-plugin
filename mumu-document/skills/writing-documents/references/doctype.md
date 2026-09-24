# Doctypes

A document answers one question. Its doctype is how it explains, picked by the
question and never by the subject; its medium is where it is read. The parts
below: doctypes, yardsticks, media, markdown forms, page, figures, prose.

## Doctypes

| doctype | answers | its parts, in order |
| --- | --- | --- |
| `diagram` | what it is made of, how its parts connect | the title; the one thing to read off it; each figure with the text it serves; its key; the source |
| `narrative` | how it works, why it is so, what will be done | a one-line thesis; a map of the whole; chapters in the order understanding builds, each headed by its one claim, each paragraph claim, reason, evidence and consequence, never a list of findings; a reason the source omits, called absent; the source at a sha |
| `comparison` | which one, what differs | the question and, in one line, what blocks it; the verdict and what would change it; the yardstick by [Yardsticks](#yardsticks), fixed before any option; each option as what of the blocker it removes, against the yardstick, bold only on the cells the verdict turns on |

- A repository's structure is a diagram, what a PR changed a comparison, why
  a design is so a narrative, a decision a comparison, and a proposal one
  among to-be plans, each with what it deletes, and leaving things as is.
- Two questions: a narrative, the diagram its map, the comparison a chapter.
- A part no fact settles is a blank: the reader's decision.
- Asked only what follows, the answer has no doctype and no parts: it skips
  every fact already on screen, says what they imply, then the one action it
  recommends, and nothing after; when nothing follows, it says so plainly
  instead of inventing a step.

## Yardsticks

A yardstick the user names but does not define is read in this sense; a
finding with no evidence a check can read is no row.

| named | measured as |
| --- | --- |
| interaction, output, structure, theory | how a person and the agents reach the result, where the person enters, decides and gets it back; what shipped, split without overlap, each part on the same criteria; simplicity, completeness, soundness, modularity, encapsulation, each measured; the one-sentence theory it rests on, judged for clarity and soundness |
| upkeep: modularity, encapsulation, simplification, unification, structural completeness, cognitive brevity | one row per finding: the module, the quality it fails, its evidence (a count, a duplicate, a reader with no consumer, a time), the follow-up |
| simpler, for a redesign | fewer components (files, entities, scripts, CI steps, prose-only rules), one shape per kind and one reader per rule, fewer dependencies: before and after counted by script, and any growth named |

## Media

- **markdown**: chat, GitHub, and always for an agent; the parts are
  headings; Mermaid only in a GitHub body.
- **page**: one HTML file for a person, when a layout, a wide table or a
  dense map outgrows markdown; it starts from `../assets/page.html`.

## Markdown forms

The smallest form that makes the point, beside the short text it supports,
with only the calls, files, states and boundaries the question needs.

| form | for |
| --- | --- |
| pseudocode | logic or an algorithm |
| a call tree | runtime control flow |
| a component tree, with the state and module boundaries that matter | UI structure |
| a shallow file tree, one comment per line | file responsibility, a broad refactor |
| a table, a row per option | a comparison |
| a diff in the shape of one of the above | a change to a shape that exists |
| the whole block | most of it is new, or a cut would hide order or ownership |

## Page

- One file: its CSS, SVG, JS and images inline, nothing fetched; opens from
  `file://`.
- Light and dark both, through the skin's tokens.
- Phone width: no sideways page scroll at 320 px, a 16 px gutter; only a
  table, a figure or code scrolls, in its own box with `tabindex="0"` and a
  label.
- No text under 11 px, no Hangul or Han under 12 px.
- `main`, `section`, `figure`, headings in order; native elements before
  ARIA; contrast 4.5:1; visible focus; every control usable by keyboard.
- Reading order is priority order; secondary work in `details`, two levels
  at most.
- The work, not the plumbing: labels, values and errors, no prose about how
  the page behaves; one fact takes one form everywhere.
- A page the reader acts on opens with one annotated sample item: each part
  named, what to press, what the answer is used for.
- No motion of its own; a transition only answers a reader's action.

## Figures

- Drawn only where it teaches more than a paragraph.
- Emphasis on 2 elements at most.
- Boxes grouped as the reader thinks of the system, never by folder.
- Coordinates divisible by 4; arrows orthogonal with r=8 elbows; a label
  8 px off its line on a background mask.
- One arrow carries a real example value; a changed flow shows before and
  after.
- Every line one-way and labelled; dashed where inferred, not read.
- A key names what was merged, collapsed or dropped; a unit on every scale.
- A compared quantity by position or length on one shared scale, never
  stacked or a pie; a bar axis starts at zero.
- Six colours at most, ground included; hue for kind, lightness for amount;
  the accent only for links and focus.
- SVG ids prefixed per figure: inline SVGs share one id space.

## Prose

- Name things instead of counting them: a count goes stale, a name can be
  grepped.
- A heading on a change says what is true after it.
- Short words, one idea a sentence, active voice; a new term is defined where
  it first appears or cut; no word that sells.
- Rules taken from outside land as a section of the existing document, only
  those it uses, with no provenance column and no skipped or not-found row.
- A Korean page keeps each term that has an English name in English, Korean
  only the grammar between, and none of `아니라`, ` 대 `, `이름하다`, `추정했다`.
- Before Check, a separate Opus editor rewrites only a Korean page's text, terms
  and `<title>` frozen; a diff of the tag stream shows only text nodes changed.

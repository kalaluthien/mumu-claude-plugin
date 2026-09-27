# Quality rubric

Grade a document a person will read, static or interactive. Score each
criterion that applies from 0 to 3 by its indicators, and quote the line or
element that sets each score below 3.

- **3**: every indicator holds.
- **2**: one lapse the reader works around.
- **1**: lapses that cost the reader time, a wrong step or a wrong belief.
- **0**: the quality is missing or misleading.

A criterion is `n/a` when its kinds exclude the document, or the document has
none of its element and needs none. The grade is a profile, one score per
dimension, the mean of its scored criteria to one decimal, never summed into
one number: `content 2.5 · structure 3.0 · language 2.0 · visual n/a ·
interaction n/a`. A dimension with every criterion `n/a` is `n/a`, never 0.
Each criterion names two or more independent sources, by author and year; the
full list, and where they agree and conflict, is in the pull request that
added this file (#272).

## Content

### Audience and purpose

The reader the document serves and what they can do after reading are plain,
and its depth fits that reader's prior knowledge. Kinds: both.

- 3: purpose and reader are stated or obvious in the first paragraph; nothing
  the reader lacks goes unexplained, nothing they know is laboured.
- 2: purpose clear; one section pitched too basic or too advanced.
- 1: purpose must be inferred, or depth fits neither a novice nor an expert.
- 0: no discernible purpose or reader.

Sources: ISO 24495-1 2023 (relevant); ISO/IEC/IEEE 26514 2022; Kalyuga et al.
2003; McNamara et al. 1996; Diátaxis.

### Accuracy and support

Every claim is correct, consistent with the rest of the document, and each
claim a reader could doubt carries its evidence: data, a citation, a runnable
example or a check. Kinds: both.

- 3: no error or contradiction; evidence sits beside each doubtable claim;
  limits and uncertainty are stated.
- 2: no error; some doubtable claims rest on assertion alone.
- 1: one error or contradiction, or a conclusion beyond the evidence shown.
- 0: several errors or contradictions.

Sources: Open Textbook Library rubric (accuracy); Nature referee guidance;
PLOS ONE criteria; Distill (integrity); Hullman and Diakopoulos 2011.

### Completeness

The document holds all its reader needs for its purpose: prerequisites, each
step or link of the argument, its limits and what to do next. Kinds: both.

- 3: a reader can act, or follow the argument, with no other source.
- 2: one gap the reader fills from general knowledge.
- 1: a gap that blocks the task or the argument: a missing step,
  prerequisite, definition of method, or a "see the code" in place of it.
- 0: the core is missing.

Sources: Open Textbook Library rubric (comprehensiveness); CONSORT 2010;
ICMJE; ISO/IEC/IEEE 26514 2022; Write the Docs (complete).

### Focus

Everything present serves the purpose; no tangent, decoration or gimmick
competes with the core. Kinds: both.

- 3: every paragraph, figure and control serves the purpose.
- 2: one digression or decoration, easy to skip.
- 1: tangents or decoration the reader must wade through.
- 0: the core is buried.

Sources: Mayer, Heiser and Lonn 2001; Mayer and Moreno 2003 (weeding);
GOV.UK content design; Hohman et al. 2020.

## Structure

### Organization

The order follows the reader's task or argument, each section has one job,
and the parts add up to one whole. Kinds: both.

- 3: order matches use (task order, argument order, simple before complex);
  each section one job; no mixing of modes, such as tutorial steps inside
  reference.
- 2: one section out of place or doing two jobs.
- 1: the reader must reassemble the order; related material is scattered.
- 0: no discernible order.

Sources: Kintsch and van Dijk 1978; Open Textbook Library rubric
(organization, modularity); Diátaxis; Segel and Heer 2010.

### Signalling

An opening overview, headings and labels let the reader predict what comes,
skim, and find a part again. Kinds: both.

- 3: the opening says what follows; each heading names its content; the
  point comes first in each section; a long document can be entered at any
  part (headings with anchors, a contents list).
- 2: one vague heading ("Notes", "Misc") or one buried point.
- 1: a long run of text with no heading, or a heading that misleads.
- 0: one unbroken wall of text.

Sources: Lorch and Lorch 1996; ISO 24495-1 2023 (findable); Mayer and Moreno
2003 (signalling); Write the Docs (skimmable, addressable); GOV.UK content
design.

## Language

### Sentence clarity

Each sentence parses on first reading: actor and action early and close
together, one idea, active voice, familiar words. Judge by reading, never by
a readability formula. Kinds: both.

- 3: nearly every sentence parses on first reading; a long one earns its
  length.
- 2: a few sentences need a second reading.
- 1: many need rereading: stacked clauses, nominalisations, a passive that
  hides the actor.
- 0: most need rereading.

Sources: Gopen and Swan 1990; ISO 24495-1 2023 (understandable); Federal
Plain Language Guidelines; Microsoft Writing Style Guide; Redish 2000.

### Cohesion

Each sentence links to the one before: known information first, new
information last, each pronoun with one clear referent, each transition naming
its relation. Kinds: both.

- 3: the reader never asks what "this" or "it" means or how a sentence
  follows from the last.
- 2: one unclear referent or missing link.
- 1: several; the reader must supply the connections.
- 0: sentences read as a list of unrelated claims.

Sources: Gopen and Swan 1990; Graesser et al. 2004; McNamara et al. 1996;
Kintsch and van Dijk 1978.

### Terminology

Each term the reader may lack is defined where it first appears, and one thing
keeps one name throughout. Kinds: both.

- 3: every such term defined at first use; one name per thing.
- 2: one undefined term or one change of name.
- 1: several undefined terms or name changes.
- 0: the reader cannot tell which names mean the same thing.

Sources: Open Textbook Library rubric (clarity, consistency); Google developer
documentation style guide; Microsoft Writing Style Guide; Write the Docs
(consistent).

## Visual

### Figure and text

A figure, table or diagram carries what prose shows poorly (a structure, a
flow, a comparison, a trend), sits beside the text it serves, and that text
refers to it. `n/a` when there is no figure and no content a figure would show
better. Kinds: both.

- 3: each figure has a stated job and a caption naming what to read off it,
  beside its text; no decorative image.
- 2: one missing caption or reference, or one figure placed far from its text.
- 1: a figure that only repeats the text or decorates, or a structure or
  comparison the prose strains to carry with no figure.
- 0: a figure that contradicts the text.

Sources: Mayer and Moreno 2003 (spatial contiguity); Butcher 2006; Mayer,
Heiser and Lonn 2001; Segel and Heer 2010.

### Data display

Charts and tables show values truthfully and readably. Check five
indicators: an honest scale and baseline; the unit of every value visible
without opening anything, on an axis, a series name or the caption; each
series named on or beside its marks, not in a distant key; exact values
available, as a table or labels; a caption that states the finding. `n/a`
without data. Kinds: both.

- 3: all five hold.
- 2: one fails.
- 1: two or more fail, or colour is the only way to tell series apart.
- 0: the display distorts the data: a truncated bar baseline, a skewed
  scale, values that differ from the source.

Sources: Cleveland and McGill 1984; Hullman and Diakopoulos 2011; WCAG 2.2
(1.1.1, 1.4.1).

### Accessibility

The presentation reaches every reader whatever their sight, device or input:
text alternatives, real headings and lists, contrast, reflow on a narrow
screen, meaning never carried by colour alone. Kinds: both.

- 3: every image and chart has a text alternative; structure is marked up,
  not faked with bold lines; no failure of WCAG 2.2 AA found.
- 2: one missing alternative or one faked heading.
- 1: several, or content lost on a narrow screen.
- 0: core content unreachable without sight or a mouse.

Sources: WCAG 2.2; Achieve OER rubrics (accessibility); Quality Matters
rubric (accessibility and usability); ISO/IEC/IEEE 26514 2022.

## Interaction

Every criterion here is `n/a` on a static document.

### Purposeful interaction

Each control lets the reader do something the purpose needs: step through a
process, vary a value, compare, open detail; the main point stays readable
without interacting, since most readers never touch a control. Kinds:
interactive.

- 3: each control serves the purpose; the default view carries the main
  point.
- 2: one control that adds little.
- 1: interaction that decorates, or core content reachable only by
  interacting.
- 0: interaction obstructs reading.

Sources: Hohman et al. 2020; Victor 2011; Moreno and Mayer 2007; Achieve OER
rubrics (technological interactivity); Yi et al. 2007; Boy et al. 2015.

### Controls

Each control is visible as a control, labelled with what it does, behaves as
its look predicts, and works by keyboard and screen reader. Kinds:
interactive.

- 3: every control has a visible label or icon with an accessible name, a
  visible focus, and keyboard operation.
- 2: one unlabelled or mouse-only control.
- 1: several, or a control that looks like text.
- 0: the reader cannot find or work the controls.

Sources: Nielsen 1994 (recognition rather than recall, consistency); WCAG 2.2
(2.1.1, 2.4.7, 4.1.2); WAI-ARIA Authoring Practices Guide.

### Feedback

Each action gets an immediate, visible response that shows what changed and
ties it to the explanation (a caption or count updates with the view).
Kinds: interactive.

- 3: every action answers at once, and the text beside it says what the
  change means.
- 2: one action whose result the reader must look for.
- 1: responses that are delayed, silent or unexplained.
- 0: actions with no visible result.

Sources: Nielsen 1994 (visibility of system status); Moreno and Mayer 2007
(feedback); Victor 2011 (reactive documents); Hohman et al. 2020.

### Navigation and state

The reader knows where they are, can go back, forward and to the start, and
can reach or share a given part or state by link. Kinds: interactive.

- 3: the current place is marked; back, forward and reset work; each part
  has its own link and the browser's back button returns to it.
- 2: one of these missing.
- 1: the reader loses their place or cannot undo a step.
- 0: the reader is trapped or lost.

Sources: Nielsen 1994 (user control and freedom); Shneiderman 1996; WCAG 2.2
(2.4, navigable); Write the Docs (addressable); Segel and Heer 2010.

### Guided exploration

The page leads from the author's path into the reader's own exploration:
an overview before detail, meaningful defaults, a cue to what to try, and
pace set by the reader. Kinds: interactive.

- 3: overview first; defaults show the telling case; the text says what to
  try; the reader sets the pace.
- 2: one of these missing.
- 1: the reader is left with controls and no path, or a fixed animation they
  cannot pause or step.
- 0: no entry point.

Sources: Segel and Heer 2010; Shneiderman 1996; Moreno and Mayer 2007
(guided activity, pacing); Kosara and Mackinlay 2013; Boy et al. 2015.

## Judge procedure

A model that grades follows these steps; the research behind each is in the
same pull request. The author's own reread applies steps 3 and 4; a grade
another person relies on takes all six.

1. **Blind.** The grader is a fresh context that did not write the document.
   It reads this rubric and the document under a neutral name, with no
   author, source, verdict or label such as "draft" or "weak".
2. **One at a time.** Each document is graded against the levels on its own,
   never against another document.
3. **Evidence first.** For each criterion, in this file's order: quote the
   line or name the element that bears on it, check each indicator, then give
   the score. With nothing falling short, the score is 3.
4. **Length earns nothing.** A longer document, section or quote scores no
   higher for its length.
5. **Two graders.** Two graders grade independently. Where they differ by one
   level, the grade is their mean; by two or more, a third grader grades that
   criterion and the median stands.
6. **Anchor set.** After this file changes, grade the documents in
   `mumu-document/tests/rubric/` again. Each criterion needs exact agreement
   on at least half the documents it applies to and agreement within one
   level on at least 80%. Each weakened copy must score lower in its weakened
   dimension and within one level in the others. A criterion under the bar is
   rewritten or dropped.

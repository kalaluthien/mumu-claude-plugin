# Quality rubric

Grade a document a person will read, static or interactive. Score each
criterion that applies from 0 to 3 by its indicators, and quote the line or
element that sets each score below 3.

- **3**: every indicator holds.
- **2**: one lapse the reader works around.
- **1**: lapses that cost the reader time, a wrong step or a wrong belief.
- **0**: the quality is missing or misleading.

Each level carries one example, made up to show the level, never taken from
a graded document. A criterion is `n/a` when its kinds exclude the document,
or the document has none of its element and needs none. The grade is a
profile, one score per dimension, the mean of its scored criteria to one
decimal, never summed into one number: `content 2.5 · structure 3.0 ·
language 2.0 · visual n/a · interaction n/a`. A dimension with every
criterion `n/a` is `n/a`, never 0. Each criterion names two or more
independent sources, by author and year; the full list, and where they agree
and conflict, is in the pull requests that built this file (#272).

## Content

### Audience and purpose

The reader the document serves and what they can do after reading are plain,
and its depth fits that reader's prior knowledge. Kinds: both.

- 3: purpose and reader are stated or obvious in the first paragraph; nothing
  the reader lacks goes unexplained, nothing they know is laboured.
  Example: "This page shows a new contributor how to run the tests; it
  assumes Git, not our build."
- 2: purpose clear; one section pitched too basic or too advanced.
  Example: a guide for operators that stops to explain what a file is.
- 1: purpose must be inferred, or depth fits neither a novice nor an expert.
  Example: a README that opens with the class hierarchy, never saying what
  the tool is for.
- 0: no discernible purpose or reader.
  Example: a page of notes titled "stuff", aimed at no one.

Sources: ISO 24495-1 2023 (relevant); ISO/IEC/IEEE 26514 2022; Kalyuga et al.
2003; McNamara et al. 1996; Diátaxis.

### Accuracy and support

Every claim is correct, consistent with the rest of the document, and each
claim a reader could doubt carries its evidence: data, a citation, a runnable
example or a check. Kinds: both.

- 3: no error or contradiction; evidence sits beside each doubtable claim;
  limits and uncertainty are stated.
  Example: "Reads are 3× faster (table 2, 10 runs, 1 GB file); writes were
  not measured."
- 2: no error; some doubtable claims rest on assertion alone.
  Example: "This is much faster" with no number beside it.
- 1: one error or contradiction, or a conclusion beyond the evidence shown.
  Example: the summary says 40% cheaper, the table beneath it 14%.
- 0: several errors or contradictions.
  Example: a setup guide whose commands, versions and paths are each wrong.

Sources: Open Textbook Library rubric (accuracy); Nature referee guidance;
PLOS ONE criteria; Distill (integrity); Hullman and Diakopoulos 2011.

### Completeness

The document holds all its reader needs for its purpose: prerequisites, each
step or link of the argument, its limits and what to do next. Kinds: both.

- 3: a reader can act, or follow the argument, with no other source.
  Example: install steps that name the version needed and end with a command
  that shows it worked.
- 2: one gap the reader fills from general knowledge.
  Example: "Restart the service" with no command, where the command is the
  usual one.
- 1: a gap that blocks the task or the argument: a missing step,
  prerequisite, definition of method, or a "see the code" in place of it.
  Example: "Configure the token as usual" in a guide for first-time users.
- 0: the core is missing.
  Example: a migration guide with no migration steps.

Sources: Open Textbook Library rubric (comprehensiveness); CONSORT 2010;
ICMJE; ISO/IEC/IEEE 26514 2022; Write the Docs (complete).

### Focus

Everything present serves the purpose; no tangent, decoration or gimmick
competes with the core. Material that belongs but gets the wrong weight is
Emphasis's. Kinds: both.

- 3: every paragraph, figure and control serves the purpose.
  Example: a bug report with the steps, the expected and the actual result,
  and nothing else.
- 2: one digression or decoration, easy to skip.
  Example: one paragraph on the project's history in an install guide.
- 1: tangents or decoration the reader must wade through.
  Example: a design note that spends half its length on rejected naming
  ideas.
- 0: the core is buried.
  Example: the one required config change hidden in a long team update.

Sources: Mayer, Heiser and Lonn 2001; Mayer and Moreno 2003 (weeding);
GOV.UK content design; Hohman et al. 2020.

## Structure

### Narrative

The order follows the reader's questions as they arise, not the writer's
work: it opens with why this reader should care, the situation and the
problem it poses for them, and moves from that problem to its resolution.
Kinds: both.

- 3: the opening says what is at stake for this reader; each section answers
  the question the one before raises; the problem leads to its resolution.
  Example: "A fix waits a day because builds take 20 minutes. Caching
  dependencies cuts that to 4; below is how, and when it does not help."
- 2: one section arrives before the reader has a reason to want it.
  Example: a full setup section placed before any word on what the setup is
  for.
- 1: the order is the writer's (the history of the work, the file order), or
  the stake comes late or never.
  Example: "First we tried Redis. Then memcached. Then ..." with the finding
  in the last paragraph.
- 0: no problem, stake or line the reader can follow.
  Example: facts listed in no order, none said to matter to anyone.

Sources: Flower 1979; Swales 1990 (create a research space); Minto 2009
(situation, complication, question); Dahlstrom 2014; Segel and Heer 2010;
Knaflic 2015.

### Pyramid and MECE

The answer comes first and each level sums up the one below: the
document's conclusion in its opening, each section's point in its first
sentence, each heading naming what its part claims. Sibling parts are
mutually exclusive and collectively exhaustive (MECE): no two cover the same
ground, and together they leave no gap in what their parent claims. Kinds:
both.

- 3: the opening states the conclusion; each section's first sentence states
  its point; siblings neither overlap nor leave a gap.
  Example: "Use a queue for work that can wait, never for a reply a user
  waits on", then one section per use, each use once.
- 2: one section whose point comes late, or one overlap or gap between
  siblings.
  Example: sections "Deploy" and "Deploying to staging" that repeat three
  steps.
- 1: the conclusion comes last or must be pieced together, or several
  overlaps or gaps.
  Example: a report whose recommendation is its closing sentence, after four
  sections of findings.
- 0: no conclusion anywhere, and groups with no logic.
  Example: headings "Misc", "More", "Other" over unrelated points.

Sources: Minto 2009; Kintsch and van Dijk 1978; Mann and Thompson 1988;
NN/g inverted pyramid; Digital.gov (most important first).

### Signalling

An opening overview, headings and labels let the reader predict what comes,
skim, and find a part again. Kinds: both.

- 3: the opening says what follows; each heading names its content; a long
  document can be entered at any part (headings with anchors, a contents
  list).
  Example: "This guide covers install, configure and upgrade", then those
  three headings, each linkable.
- 2: one vague heading ("Notes", "Misc").
  Example: a heading "Details" over the error codes.
- 1: a long run of text with no heading, or a heading that misleads.
  Example: a heading "Install" over the uninstall steps.
- 0: one unbroken wall of text.
  Example: a two-thousand-word page in one paragraph.

Sources: Lorch and Lorch 1996; ISO 24495-1 2023 (findable); Mayer and Moreno
2003 (signalling); Write the Docs (skimmable, addressable); GOV.UK content
design.

### Emphasis

Weight follows importance: the key point gets the most prominent place (the
opening, a heading, a first or last sentence) and the space it needs, and a
minor point gets less. Kinds: both.

- 3: after one skim the reader can name the key point; space is spent in
  order of importance.
  Example: the decision in the first sentence and its own section; caveats
  in a short list at the end.
- 2: one minor point given more space or prominence than it merits.
  Example: three paragraphs of background before a one-line result.
- 1: the key point buried: mid-paragraph, under a minor heading, or given the
  least space of any part.
  Example: the dropped platform named once, mid-paragraph, under "Other
  notes".
- 0: everything weighted alike, or so much bold that nothing stands out.
  Example: every other sentence in bold.

Sources: Williams and Bizup 2014 (emphasis, concision); Minto 2009 (order of
importance); Lemarié et al. 2008; Mautone and Mayer 2001; NN/g F-shaped
reading.

## Language

### Sentence clarity

Each sentence parses on first reading: actor and action early and close
together, one idea, active voice, familiar words. Judge by reading, never by
a readability formula. Kinds: both.

- 3: nearly every sentence parses on first reading; a long one earns its
  length.
  Example: "The server drops a request after 30 seconds."
- 2: a few sentences need a second reading.
  Example: "Requests, which after 30 seconds, unless retried, are dropped."
- 1: many need rereading: stacked clauses, nominalisations, a passive that
  hides the actor.
  Example: "Implementation of timeout enforcement is performed upon request
  receipt."
- 0: most need rereading.
  Example: a page where nearly every sentence reads like the one above.

Sources: Gopen and Swan 1990; ISO 24495-1 2023 (understandable); Federal
Plain Language Guidelines; Microsoft Writing Style Guide; Redish 2000.

### Cohesion

Each sentence links to the one before: known information first, new
information last, each pronoun with one clear referent, each transition naming
its relation. Kinds: both.

- 3: the reader never asks what "this" or "it" means or how a sentence
  follows from the last.
  Example: "The cache holds 64 MB. That size keeps 88% of reads off the
  disk."
- 2: one unclear referent or missing link.
  Example: "The cache and the pool both grow. It is capped at 64 MB."
- 1: several; the reader must supply the connections.
  Example: a paragraph of claims joined only by "also".
- 0: sentences read as a list of unrelated claims.
  Example: "Caches help. Disks fail. Use version 3."

Sources: Gopen and Swan 1990; Graesser et al. 2004; McNamara et al. 1996;
Kintsch and van Dijk 1978.

### Coherence

The whole document keeps one thread: each section advances the same purpose
and its link to it is plain, and the viewpoint (who speaks, to whom) and the
tone stay the same throughout. The links between neighbouring sentences are
Cohesion's. Kinds: both.

- 3: every section ties back to the one thread; one voice and register
  throughout.
  Example: each section opens with the part of the question it answers;
  "you" throughout.
- 2: one section whose link to the thread the reader must infer, or one
  shift of voice or tone.
  Example: one "the user shall" paragraph in a page written to "you".
- 1: sections that read as separate pieces, or a tone that swings between
  chatty and formal.
  Example: a design note stitched from three authors, each with its own aim.
- 0: no thread: the parts do not make one document.
  Example: meeting notes, a changelog and a tutorial pasted under one title.

Sources: Halliday and Hasan 1976; Grosz and Sidner 1986; Albrecht and
O'Brien 1993; McNamara et al. 1996; Hyland 2005.

### Terminology

Each term the reader may lack is defined where it first appears, and one thing
keeps one name throughout. Kinds: both.

- 3: every such term defined at first use; one name per thing.
  Example: "A shard, one slice of the table, lives on one node."
- 2: one undefined term or one change of name.
  Example: "shard" in one section, "partition" for the same thing in the
  next.
- 1: several undefined terms or name changes.
  Example: "WAL", "LSN" and "fsync" in a beginner's guide, none explained.
- 0: the reader cannot tell which names mean the same thing.
  Example: "node", "host", "box" and "instance", sometimes the same thing,
  sometimes not.

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
  Example: a request-flow diagram captioned "a retry goes back to the queue,
  never to the client", beside the retry section.
- 2: one missing caption or reference, or one figure placed far from its text.
  Example: an architecture diagram with no caption, at the page's end.
- 1: a figure that only repeats the text or decorates, or a structure or
  comparison the prose strains to carry with no figure.
  Example: six services and their calls described in one paragraph, no
  diagram.
- 0: a figure that contradicts the text.
  Example: the text says A calls B; the diagram's arrow runs from B to A.

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
  Example: bars from zero labelled "ms", each bar valued at its end, the
  caption "p95 halved after the fix".
- 2: one fails.
  Example: the same chart captioned only "Latency".
- 1: two or more fail, or colour is the only way to tell series apart.
  Example: two lines told apart only by red and green, no unit anywhere.
- 0: the display distorts the data: a truncated bar baseline, a skewed
  scale, values that differ from the source.
  Example: a bar axis starting at 90% so that 92% looks twice 91%.

Sources: Cleveland and McGill 1984; Hullman and Diakopoulos 2011; WCAG 2.2
(1.1.1, 1.4.1).

### Accessibility

The presentation reaches every reader whatever their sight, device or input:
text alternatives, real headings and lists, contrast, reflow on a narrow
screen, meaning never carried by colour alone. Kinds: both.

- 3: every image and chart has a text alternative; structure is marked up,
  not faked with bold lines; no failure of WCAG 2.2 AA found.
  Example: a chart with its data table in a disclosure, headings as `h2`, a
  320 px layout with no sideways scroll.
- 2: one missing alternative or one faked heading.
  Example: one screenshot with no alt text.
- 1: several, or content lost on a narrow screen.
  Example: bold paragraphs posing as headings, and a table cut off on a
  phone.
- 0: core content unreachable without sight or a mouse.
  Example: the result shown only in a canvas image, reached only by
  dragging.

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
  Example: a slider over the interest rate beside the text "at 5% savings
  double in 14 years", which reads without moving it.
- 2: one control that adds little.
  Example: a colour-theme switch on an explainer.
- 1: interaction that decorates, or core content reachable only by
  interacting.
  Example: the key figure shown only while hovering one point of a chart.
- 0: interaction obstructs reading.
  Example: a quiz that must be answered before the text appears.

Sources: Hohman et al. 2020; Victor 2011; Moreno and Mayer 2007; Achieve OER
rubrics (technological interactivity); Yi et al. 2007; Boy et al. 2015.

### Controls

Each control is visible as a control, labelled with what it does, behaves as
its look predicts, and works by keyboard and screen reader. Kinds:
interactive.

- 3: every control has a visible label or icon with an accessible name, a
  visible focus, and keyboard operation.
  Example: `<label>Interest rate <input type="range">`, outlined on focus,
  moved by arrow keys.
- 2: one unlabelled or mouse-only control.
  Example: one gear icon button with no accessible name.
- 1: several, or a control that looks like text.
  Example: links styled as plain text, and a `div` that acts as a button with
  no role.
- 0: the reader cannot find or work the controls.
  Example: a chart that changes only when dragged, with no sign it can be.

Sources: Nielsen 1994 (recognition rather than recall, consistency); WCAG 2.2
(2.1.1, 2.4.7, 4.1.2); WAI-ARIA Authoring Practices Guide.

### Feedback

Each action gets an immediate, visible response that shows what changed and
ties it to the explanation (a caption or count updates with the view).
Kinds: interactive.

- 3: every action answers at once, and the text beside it says what the
  change means.
  Example: moving the rate slider updates the doubling time and the sentence
  under it at once.
- 2: one action whose result the reader must look for.
  Example: a filter that changes a count at the page's bottom, off screen.
- 1: responses that are delayed, silent or unexplained.
  Example: a table that re-sorts on a click, with nothing saying by what.
- 0: actions with no visible result.
  Example: a "Recalculate" button that changes nothing on screen.

Sources: Nielsen 1994 (visibility of system status); Moreno and Mayer 2007
(feedback); Victor 2011 (reactive documents); Hohman et al. 2020.

### Navigation and state

The reader knows where they are, can go back, forward and to the start, and
can reach or share a given part or state by link. Kinds: interactive.

- 3: the current place is marked; back, forward and reset work; each part
  has its own link and the browser's back button returns to it.
  Example: a contents list marking the chapter shown, a pager, and a
  `#chapter` link per part.
- 2: one of these missing.
  Example: chapters with a pager but no link to share one.
- 1: the reader loses their place or cannot undo a step.
  Example: a wizard whose back button clears the answers given.
- 0: the reader is trapped or lost.
  Example: a step-through with no back button and no way to restart.

Sources: Nielsen 1994 (user control and freedom); Shneiderman 1996; WCAG 2.2
(2.4, navigable); Write the Docs (addressable); Segel and Heer 2010.

### Guided exploration

The page leads from the author's path into the reader's own exploration:
an overview before detail, meaningful defaults, a cue to what to try, and
pace set by the reader. Kinds: interactive.

- 3: overview first; defaults show the telling case; the text says what to
  try; the reader sets the pace.
  Example: "Start at 5%, then try 10% and compare", with the slider at 5%.
- 2: one of these missing.
  Example: good defaults, but no word on what to try.
- 1: the reader is left with controls and no path, or a fixed animation they
  cannot pause or step.
  Example: a map with twelve filters and no sentence on where to start.
- 0: no entry point.
  Example: a page of sliders with no text.

Sources: Segel and Heer 2010; Shneiderman 1996; Moreno and Mayer 2007
(guided activity, pacing); Kosara and Mackinlay 2013; Boy et al. 2015.

## Judge procedure

A model that grades follows these steps; the research behind each is in the
same pull requests. The author's own reread applies steps 3 and 4; a grade
another person relies on takes all six. Each step says whether its effect
was shown on this rubric or is unproven.

1. **Blind.** The grader is a fresh context that did not write the document.
   It reads this rubric and the document under a neutral name, with no
   author, source, verdict or label such as "draft" or "weak".
   Shown: with a reviewer's verdict shown, 9 criteria moved toward the
   verdict and none against, and the strong-weak gap narrowed in every
   dimension (#280).
2. **One at a time.** Each document is graded against the levels on its own,
   never against another document.
   Unproven: no run grading two documents together was made; kept because
   pairwise judging flips on distractors far more often (Tripathi et al.
   2025).
3. **Evidence first.** For each criterion, in this file's order: quote the
   line or name the element that bears on it, check each indicator, then give
   the score. With nothing falling short, the score is 3.
   Unproven: on 10 anchors, graders who gave scores alone agreed with each
   other on 85% of cells, against 87% and 90% in two runs with this step,
   and equally (67%) on the 21 cells where graders had split; kept because
   reasoning before the score reduces judge bias (Soumik 2026).
4. **Length earns nothing.** A longer document, section or quote scores no
   higher for its length.
   Unproven: without it, graders agreed on 87% of cells, the same as a run
   with it, and on 67% of the split cells either way; kept because judges
   still favour length (Zheng et al. 2023; Dubois et al. 2024).
5. **Two graders.** Two graders grade independently. Where they differ, a
   third grader grades the document, and each criterion they split on takes
   the median of the three scores, the lower middle when one is `n/a`; `n/a`
   stands when two of three give it.
   Unproven: no human labels exist to show that the settled score is closer
   to the truth than one grader's; kept because it makes each disagreement
   visible and settles it by rule (Verga et al. 2024).
6. **Anchor set.** After this file changes, run
   `"${CLAUDE_PLUGIN_ROOT}/skills/writing-documents/scripts/grade.py"`: it
   grades the documents in `mumu-document/tests/rubric/` by steps 1 to 5 and
   prints each criterion's agreement with `answer-key.json` there, each
   document's profile, and each weakened copy against its base. Each
   criterion needs exact agreement with the key on at least half the
   documents it applies to and within one level on at least 80%; each
   weakened copy scores lower in its weakened dimension and within one level
   in the others. A criterion under the bar is rewritten or dropped; a new
   document or criterion enters the key from a `grade.py --write-key` run.
   Shown: in #280 the anchor set caught Data display under the bar twice,
   and its rewrite passed.

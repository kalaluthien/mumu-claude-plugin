import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # scripts/
TEMPLATES = os.path.join(HERE, '..', 'templates')

# ---------------------------------------------------------------- policies, bands, defaults
POLICIES = {
    'scale': {'book': 'map unit 0, parts, nav, appendix with legend, notation, glossary', 'sections': 'map optional, nav', 'page': 'one unit, 1-3 questions, no nav'},
    'selection': {'minimum': 'unreachable concepts and units serving no question are errors', 'source': 'same, as warns', 'survey': 'off'},
    'structure': {'project': 'core units take earlier facts, make new ones, show a step', 'ladder': 'facts chain, step optional', 'none': 'off'},
    'interaction': {'full': 'probe per core unit, ask and task cards gating the text, close with interleaved review', 'light': 'probe and close only; still gating', 'none': 'static text; probe and close optional'},
    'length': {'rich': 'high bands', 'standard': 'middle bands', 'brief': 'low bands'},
    'review': {'full': 'every unit through every lens of the panel', 'sample': 'the map, the capstone and one core unit per part'},
}
DEFAULT_POLICY = {k: next(iter(v)) for k, v in POLICIES.items()}
ROLES = ('map', 'core', 'capstone', 'catalog', 'ref')
TACTICS = ('color', 'geom', 'iso', 'metaphor', 'frames', 'fork', 'multiples', 'plot', 'table')
MARKS = ('fill', 'line', 'dash', 'dot')
KINDS = ('semantic', 'categorical', 'sequential', 'diverging', 'cyclic')  # lexicon kinds; ordered kinds are ramps of entries sharing `ramp`
TIERS = ('toy', 'scaled', 'real')
Q_COUNT = {'book': (2, 9), 'sections': (1, 6), 'page': (1, 3)}
BANDS = {  # role -> (min, max) for chars, figs, ex, defs, qs (cards); tactics = distinct figure tactics in a core unit
    'rich': {'core': dict(chars=(8000, 16000), figs=(3, 8), ex=(2, 4), defs=(1, 6), qs=(6, 14), tactics=2),
             'map': dict(chars=(1500, 8000), figs=(0, 5)), 'capstone': dict(chars=(4000, 14000), figs=(2, 8)), 'catalog': dict(chars=(1500, 9000), figs=(1, 6))},
    'standard': {'core': dict(chars=(4000, 10000), figs=(2, 6), ex=(1, 3), defs=(1, 6), qs=(4, 10), tactics=2),
                 'map': dict(chars=(800, 6000), figs=(0, 4)), 'capstone': dict(chars=(2500, 10000), figs=(1, 6)), 'catalog': dict(chars=(800, 7000), figs=(0, 5))},
    'brief': {'core': dict(chars=(600, 6000), figs=(1, 4), ex=(0, 2), defs=(1, 4), qs=(3, 8), tactics=1),
              'map': dict(chars=(200, 4000), figs=(0, 3)), 'capstone': dict(chars=(600, 5000), figs=(1, 4)), 'catalog': dict(chars=(300, 5000), figs=(0, 4))},
}
COMMON = dict(novelty=0.6, novelty_window=1500, fact_max=25, opener_max=2, key_max=90, elab_min=500, len_ratio=1.25, apply_share=0.4, max_categorical=3, contrast=3.0, cvd_dl=0.08, alt_words=5, gist=(2, 4), mean_sentence=35, short_sentence=25, max_short_share=0.35, overlap=0.5, repeat_min=40, max_text_native=12, path_names=5)
UI_KEYS = ('locked', 'toc', 'dark', 'light', 'top', 'pan', 'node', 'go', 'back', 'pick', 'retry', 'right', 'check', 'up', 'down', 'move', 'pool', 'place', 'answer', 'play', 'pause', 'prev', 'next')
SCHEMA = {  # key -> required fields of each entry
    'questions': ('id', 'text', 'answer', 'needs'), 'concepts': ('id', 'term', 'unit'), 'units': ('id', 'role', 'title'),
    'lexicon': ('id', 'meaning', 'mark', 'light'), 'homes': ('id', 'meaning', 'regions'), 'symbols': ('tex', 'meaning'),
    'forbid': ('id', 're', 'example'), 'decisions': ('node', 'chosen'),
}
FORBID_KEYS = {'id', 're', 'in', 'unless', 'level', 'fix', 'example'}

RULES = {
    'B1': ('error|warn', 'Questions: count per scale, needs resolve, answer present; every concept reachable from a question; every core or capstone unit serves one', 'Level follows `selection`'),
    'B2': ('error|warn', 'Concept needs acyclic, each need homed no later; facts taken after they are made or declared given; final fact made; most core units make one', ''),
    'B3': ('error|warn', 'Lexicon: unique id, meaning, color-mark pair; kind in KINDS; ordered ramps (entries sharing `ramp`): sequential lightness monotone, diverging has one `mid` step that is lightest, cyclic ends match; entries sharing a mark differ in lightness by cvd_dl (hue alone fails colour-vision deficiency); categorical cap (owner taste); graphic contrast in both themes; homes list regions', 'Contrast uses the template background'),
    'B4': ('error|warn', 'Schema fields present; book.emphasis set; canon kinds compile; ids unique and resolvable; roles, parts, titles; symbol scopes disjoint; forbid entries compile, match their example, use known keys; policies valid; a stored concept final agrees with the derived reading', ''),
    'B5': ('error|warn', 'Gates: live units need a recorded skeleton gate; round 1 carries directives on figures, cards, terms boxes and deep models; new_patterns holds a new problem and a new visual pattern (book.policies.new_patterns each) with nearest and differs, ids new to the catalog; the newest gate record carries the current plan hash (no silent plan change)', 'Re-record the gate after the user sees the change; a skeleton approved before new_patterns existed warns'),
    'G1': ('error', 'Chrome (data-d) present where required and equal to a fresh render of book.json; every planned unit built, no unplanned unit', 'Rebuild after any plan edit'),
    'G4': ('error', 'Markup: tags balance inside every unit (the first unclosed or stray element is named with its block id); every id appears once in the book', 'Fix the unit source; `edit --patch` refuses a result that changes the balance'),
    'G2': ('error|warn', 'data-ref targets, text and gloss, data-v facts and data-variant-of ids resolve (a variant varies an earlier unit\'s card); no leaked build tokens; no hand-typed unit number', ''),
    'U1': ('error|warn', 'Unit shape per role: gist first, probe next, close last, step when the unit makes facts; gist 2-4 sentences', ''),
    'U2': ('error|warn', 'Probe: one per unit, right after the gist; its wording avoids the mechanism and terms this or later units define (it may name the topic). Insight sentences link their concept with data-ref', ''),
    'U3': ('error|warn', 'Each concept defined once, in its home unit; in a core unit each defn holds a one-sentence key, the key is followed by rich elaboration, and a frames figure builds the concept step by step', ''),
    'U4': ('error|warn', 'Cards: a stem; choice cards one data-ok and a why on every option; examples open with a worked step and give 2+ steps the reader takes; tasks well formed per kind, and only machine-checkable kinds (no free-text compose: a reader could never pass it); close has a summary paragraph and a review variant; grade and badge vocabularies; no hover-only information', ''),
    'U5': ('error', 'Notes and asides fold as details with a summary; legend and notation only in the appendix', '-'),
    'K1': ('warn|error', 'Option length and position cue: per card the answer is over 1.25x the longest or under 1/1.25x the shortest wrong one; per unit or book the answer sits first or last after length ordering far above chance', 'A one-term answer beside longer wrong ones'),
    'K3': ('warn', 'Absolutes or negations (always, never, only; the pack\'s `cue_words`) appear in wrong options or false sentences but not in the right one', 'A true universal claim'),
    'K4': ('error', 'Catch-all options: all or none of the above, both, cannot tell', '-'),
    'K5': ('warn', 'The answer copies a long run of the unit prose and no wrong option does', 'Re-asks in reviews are exempt'),
    'K6': ('warn|error', 'Card move: every card carries data-move from MOVES; a core unit has a predict, intervene, decide or diagnose card; per book compute is under 40% of moves', 'Procedural books: allow'),
    'K7': ('warn', 'Option craft (KICE, Haladyna): stem ends as a question; negations underlined; 3-5 options outside examples, one count per book; one grammatical shape; options exclusive', '-'),
    'K8': ('error|warn', 'Card metadata and coverage: data-level (Bloom) and data-diff on every card; a production task (order, estimate or custom) per core unit; apply-or-higher share; all difficulties; order, estimate and custom tasks in the book', 'Procedural or reference books: allow'),
    'K9': ('error|warn', 'Novelty: an apply-level answer does not restate the prose just above it; the gist does not give away the probe; two cards in a unit do not share an answer; a review variant does not repeat its source stem', '-'),
    'K10': ('warn', 'Rival parity: vague or extreme words only in wrong options; only the answer concrete (numbers and Latin names counted per option, 2+ more in the answer); a sort item naming its own category', 'Options that are exhibits are skipped'),
    'K12': ('warn', 'A wrong option\'s why rests on a number or Latin name that the stem, the card\'s exhibits, the options and the unit before the card never gave and that one arithmetic step cannot derive', '-'),
    'K13': ('warn', 'An option ends in a label for its type of answer (the pack\'s `label_end`, such as "the cautious answer") instead of the move itself', '-'),
    'O4': ('warn', 'A card stem or worked step points at material it does not show (this draft, sentence 3, the table above; the pack\'s `unseen_ref`) and the card or example holds no exhibit', 'Material quoted in the stem itself: allow in decisions'),
    'F8': ('error', 'Every figure and image exhibit has an alt (aria-label) of alt_words+ words (pack) that is not an id; a frame counts its own caption; a one-word label fails even beside a long caption, and any role=img svg or img outside the exhibits needs 2+ words', '-'),
    'F9': ('warn', 'A sentence lists four or more short parts (pack `list_sep`, `list_item` words each, no clause endings) and its section has no figure: a structure narrated, not drawn', 'A list that is no structure: allow in decisions'),
    'U6': ('warn', 'Three or more study notes before a section\'s first card and no frames, example or step in the section: studies merged without a case', '-'),
    'V2': ('warn', 'A formula block (eqp, drv, formal) before the section\'s first terms box; a symbol defined in running prose (the pack\'s `symbol_def`)', '-'),
    'T3': ('warn', 'A fact whose value is a comma list is spliced before a particle (the pack\'s `list_splice`)', 'Packs without particles skip it'),
    'S6': ('warn', 'One Latin name glossed with two native spellings across units, as native(Latin)', '-'),
    'C2': ('warn', 'A running-case quantity (word + number + pack `counters`, in step blocks or sentences naming the project, canon values or canon.names) takes two values across units; hypothetical sentences (pack `hypothetical`) exempt', 'A value that changes in the story: say so, allow in decisions'),
    'C3': ('warn', 'One running-case number written two ways (separator, decimals) or against canon.format.thousands', '-'),
    'E1': ('warn', 'A prose sentence with a percentage, a sample size or a causal finding (pack `quant`, `causal`) and no data-cite, badge, year citation in its block', 'Cards, notes, examples and steps skipped'),
    'E2': ('warn', 'A data-cite names no note, or its sentence uses a hedge form of a stronger grade than the cited note (book.strings.hedges, else the pack\'s `hedges` by grade rank)', '-'),
    'E3': ('warn', 'Study notes: fields as p[data-p=design|found|limits|source], labels from strings.note_parts; a design without a sample size (pack `sample`, unless `no_sample`); a source without a link; a note missing its source or limits part', 'Free-text notes: one warn per unit'),
    'K11': ('warn', 'A wrong option\'s why concedes it (true but; the pack\'s `concede`): a second answer', '-'),
    'R1': ('warn', 'Register: card text leaves the book register; stems or instructions end in several registers', 'Quoted sample text: data-quote'),
    'O2': ('warn', 'A badge in mid-paragraph reads into the following words', '-'),
    'L4': ('warn', 'Formula openings: 3+ paragraphs or feedback lines in a unit open with the same words', '-'),
    'F7': ('warn', 'A prose paragraph names path_names or more distinct system names (Latin-letter tokens: hosts, files, paths, services) and its section (heading to heading) has no figure: a path or structure narrated, not drawn', 'A paragraph that only lists names: draw the list or allow it in decisions'),
    'O3': ('warn', 'A card stem or option reads a record, screen or command output (a sources[] form) before the block marked data-see for that source, or a source has no such block', 'A source the reader already knows: drop it from sources'),
    'F6': ('warn', 'Prose points at a frame or an option by position (the fourth frame, the first option; the pack\'s `pos_ref`) though frames play on their own and build reorders options', '-'),
    'S4': ('warn', 'An avoided form (concepts[].avoid, terms[].avoid) in prose or figure labels; a gloss in parentheses right after the used form is exempt', '-'),
    'C1': ('warn', 'A case constant (a token matching a canon.kinds pattern) that is not a canon value', 'A real outside value quoted as is (a vendor range): declare it as a value'),
    'L5': ('warn', 'The same word or phrase twice in a row in the built text, often a literal word beside a ref that fills in the same word', '-'),
    'S5': ('warn', 'Strings that land inside the prose (refs, kickers, labels, grades, badges) are not in the content language', '-'),
    'H1': ('warn', 'A section heading is a question or a sentence; headings are noun phrases', '-'),
    'T2': ('error|warn', 'A fact is a short noun phrase (no colon, arrow or brackets, under fact_max chars); one spliced into 3+ units is recalled in fresh words', '-'),
    'S2': ('error', 'Fourth-wall narration: the book talks about its own making, scope decisions, other artifacts, the requester or earlier versions', 'Quote such words inside a source quotation only'),
    'V1': ('warn', 'A paragraph defines three or more named parts inline (a symbol or term followed by is or means; the pack\'s `inline_def`); put the vocabulary in a terms box (div[data-c=terms] with one dt and dd per name)', 'A sentence that only names parts without defining them: allow in decisions'),
    'S3': ('warn', 'Translationese: the language pack\'s `translationese` forms', 'Keep a form chosen on purpose; allow in decisions'),
    'P1': ('error', 'Slots (slots/U.json): every <!--card ID--> or <!--fig ID--> has an entry and every entry a placeholder; known kind and elements the kind can hold; required slots present, typed, not TODO; element counts per kind. Build refuses on any', '-'),
    'P2': ('error|warn', 'Element checks on slot entries (catalog/elements/*.json checks): stem-self-contained, facts-shown, why-grounded, no-leak, rival-real, near-miss-names, differs-one, parts-match, one-change, items-fit, given-shown, axes, direct-labels, alt-complete and the rest', 'why-grounded counts prior prose, terms and canon as known'),
    'G3': ('warn', 'A concept with no aliases: search and the glossary find it only by its exact term', 'A term with no other form in use: allow in decisions'),
    'S1': ('per entry', 'book.json forbid entries over prose, TeX or figure labels, with `unless` exemptions', 'Exempt matches with `unless`'),
    'T1': ('error', 'Korean particle after a concept term or alias (final derived from a Hangul or digit ending, else `final`), or after any filled reference or fact ending in Hangul, a digit or %, disagrees with its final sound (lang ko)', 'Text ending in Latin letters or TeX is checked only through `final`'),
    'O1': ('warn', 'Concept term used before its home unit without a data-ref link in the same block', 'Map, ref units and probes exempt'),
    'M1': ('warn', 'Registered symbol used outside its scope', 'Sub- and superscripts and letters inside \\mathbb{}, \\mathrm{}, \\text{} are skipped'),
    'M2': ('error', 'Asymmetric symbol (or one of its `forms`) written as an equality with swapped arguments', ''),
    'M3': ('warn', 'Long Hangul text inside \\text{} in TeX', ''),
    'F1': ('error|warn', 'SVG colors only via lexicon classes (lx-ID) or neutrals; lx classes declared in the figure data-enc', 'fill="none", currentColor and url() allowed'),
    'F2': ('error|warn', 'Tactic and kind valid; home figures never in the map, drawn first where first needed, later instances name a focus region, each home recurs; frames have 3+ frames and a read line; core captions; controls below the figure', ''),
    'F5': ('error', 'A figure inside a warn, gist, key or card', '-'),
    'F3': ('warn', 'Figure count and distinct tactics inside the role band', ''),
    'F4': ('error', 'Selectable diagrams: every data-node has a data-note, node ids unique in the figure, every data-edge names two nodes of the figure', ''),
    'L1': ('warn', 'Characters, worked examples, definitions and question cards inside the role band', 'Set bands from `stats`'),
    'L2': ('warn', 'Sentence rhythm: mean length and short-sentence share', 'Skipped by --quick'),
    'L3': ('warn', 'Summary repeats a warn box; one sentence repeated across units', 'Skipped by --quick'),
}

WRITE_SECTIONS = ('shape', 'sentences', 'cards', 'figures', 'evidence')  # the sections of reference/write.md that the writer brief names
REF_OF = {'R': 'reference/write.md#sentences', 'T': 'reference/write.md#sentences', 'S': 'reference/write.md#sentences', 'L': 'reference/write.md#sentences', 'M': 'reference/write.md#sentences',
          'U': 'reference/write.md#shape', 'H': 'reference/write.md#shape', 'G': 'reference/write.md#shape', 'V': 'reference/write.md#shape',
          'K': 'reference/write.md#cards', 'P': 'reference/write.md#cards', 'G3': 'reference/plan.md', 'F': 'reference/write.md#figures', 'O': 'reference/write.md#evidence', 'C': 'reference/review.md#lens: coherence', 'E': 'reference/write.md#evidence', 'O4': 'reference/write.md#cards',
          'B': 'reference/plan.md', 'B5': 'reference/plan.md#new-patterns', 'G4': 'reference/write.md#shape', 'O1': 'reference/write.md#shape', 'O3': 'reference/write.md#shape', 'U4': 'reference/write.md#cards', 'K9': 'reference/review.md#lens: items', 'L3': 'reference/review.md#lens: editor'}
MOVES = ('predict', 'intervene', 'explain', 'decide', 'diagnose', 'compute')
LEVELS = ('remember', 'understand', 'apply', 'analyze', 'evaluate', 'create')
TASK_KINDS = ('order', 'select', 'sort', 'estimate', 'custom')  # every gating card is machine-checkable; free text (compose) cannot gate
INLINE_STRINGS = ('kicker', 'part', 'ref', 'aside', 'lab_ex', 'lab_warn', 'lab_step', 'lab_close')
LABELED = ('ex', 'warn', 'step', 'close')


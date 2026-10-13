# Skills and agents

**Underivable only**: write only what the reader cannot derive: house conventions, defaults that
surprise, values that must match another file. An `agents/*.md` file takes a
skill's frontmatter rules; its body is the delegate's system prompt.

**Delegates**: a delegate's report is its final message, never a file it writes: the brief
asks for it so. A slash command in a delegate's prompt is plain text: the brief
names the skill for it to call.

**Lesson filed**: a procedure belongs to the skill that owns the work,
edited in its source, never in the plugin cache, or a new skill in
`~/.claude/skills/`, as the steps as run with what varied as parameters; how
a delegate should work belongs to its `agents/<name>.md`.

## Folder

- **Placement**: where each file sits, and how one links another: the repository's `AGENTS.md`.
- **Moves**: moving a file or a rule: `git mv`, then search the plugin and its checks
  for the old path and bare name until none is stale, and open each
  new link once, because a stale path fails only when that step runs. A
  moved rule is re-derived against each member of its new home, and the old
  home emptied only once a grep of the destination finds the rule's nouns.
- **Directory marketplace**: a `directory` marketplace loads plugins from its checkout, so a pulled
  merge needs no update and a worktree's edit reaches no session.
- **Sweeps**: a sweep's zero counts only once its pattern has found one known hit. List
  the surfaces first: the tracked tree, untracked files, other checkouts,
  every memory pool, issue and pull request bodies. Sweep a hyphenated name
  with any separator and any case, and a moved rule by its vocabulary.
  Re-read each edited file top to bottom, since the survivor sits nearest the
  correction.
- **No `skill.md`**: no file under a skill is named `skill.md` in any case: on a case-insensitive
  filesystem it is `SKILL.md`.

## Frontmatter

- **`name`**: the directory's name, a gerund with its object when the model loads
  it.
- **`description`**: one `Use when …` sentence that classifies the situation
  without restating the body, in the third person, with no list of typed
  words and no angle brackets, since the listing truncates. A `Not for …`
  clause names the sibling that could claim the same request, because
  negative scope stops over-triggering and more positive description does
  not. Count firing in live `claude -p --output-format stream-json` runs,
  since `plugin eval` overstates it.
- **Invocation**: `disable-model-invocation: true` on a skill only a person types, its
  description saying what it does; `user-invocable: false` on one only the
  model loads.
- **Unread keys**: a key the build does not read is accepted in silence: confirm a key by what
  the session's skill list shows, never by the absence of an error.
- **Not yours**: a skill whose file is not yours to edit: a `Skill(<name>)` deny rule in a
  settings file stops the model's call only; the typed form still runs.
- **Free-form text**: a skill a person types takes free-form text: it finds what it needs
  anywhere in it, asks for what is missing, and never refuses for wording; its
  `argument-hint` is a plain example, not a grammar.

## Body

**Sections**: zero to three sections, ordered so the reader meets each when it applies:
a small rule from first principles, a few worked examples for a subject thick
with exceptions, a definition for a term, or a catalogue for distinct
situations, the situation in one column and the action in the next. A row
that selects a whole mode links a file in `references/`; a reference no row
names is never read, and one over 100 lines opens with a summary.

**By trigger**: split by the trigger, not by the content: variants of one situation stay one
skill, each variant a reference.

**Entry skill**: an entry skill exists only for work started on purpose, a person or an agent
handing work over. Its `SKILL.md` is a routing table, each row a situation in
the words a person would use and its playbook, tried in order with a fallback
row last; the agent copies that playbook's steps verbatim into its todo list,
because a paraphrase drops them. A check every playbook needs runs after the
match, and a step cited from another playbook is named with it.

**Batches**: a skill that asks the owner in batches loops within the same call until
nothing is left but what the owner rejected, never deferring the rest to a
next run, because the owner invoked it to finish the job.

## Register

**Cut first**: cut a rule before you shorten it: compliance falls with the number of rules
held at once. Plain imperatives, no capitals; keep a prohibition a
prohibition. One term per concept, no dates or versions, no constant without
the reason for its value. An example that repeats its instruction anchors
the agent to the sample instead of the rule.

- **Consumer**: write a rule's consumer in the same change, with hostile cases.
- **Conditional rules**: a conditional rule loads when the agent opens a matching file with `Read`,
  never on a write or a shell read: scope it to paths the agent will open.
- **Replacement rules**: a replacement rule gets a forward pass, what it now refuses, and a backward
  pass, what leaned on the old shape; a rule stated twice is fixed twice.

**Vendored**: a vendored skill is a byte-identical copy of its upstream, named on the first
line of its body, so an upgrade replaces the whole file.

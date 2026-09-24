# Skills and agents

Write only what the reader cannot derive: house conventions, defaults that
surprise, values that must match another file. An `agents/*.md` file takes a
skill's frontmatter rules; its body is the delegate's system prompt.

A lesson filed here: a procedure goes into the skill that owns the work,
edited in its source and never under `~/.claude/plugins/cache/`, or a new one
in `~/.claude/skills/`, as the steps as run with what varied between runs as
parameters; how a delegate should work goes into its `agents/<name>.md`.
The parts below: folder, sweeping, frontmatter, body, register.

## Folder

- A skill folder holds `SKILL.md` and only `references/` (documents it loads),
  `scripts/` (code it runs) and `assets/` (files it copies), because a reader
  then knows what a file is for from where it sits. A file two skills use
  lives in the one whose steps build with it, else the one with the broadest
  trigger, and the others link that path. At a plugin's root sit only folders
  the harness or several skills run (`bin/`, `hooks/`, `monitors/`, `agents/`,
  `lib/`), never a loose document.
- A skill links its own files by relative path, and another skill's by
  `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/...`, because the relative form breaks
  when read from outside the folder.
- Moving a file: `git mv`, then search the plugin (skills, hooks, `bin/`,
  tests, eval grader patterns) for the old path and the bare file name until
  neither is found stale, then open each new link once, because a stale path
  fails only when that step runs.
- Moving a rule: re-derive it against each member of its new home, and empty
  the old home only once a grep of the destination finds the rule's nouns.
- A `directory` marketplace loads plugins from its checkout, so a merge pulled
  there needs no update and a worktree's edit reaches no session.
- No file under a skill is named `skill.md` in any case: on a case-insensitive
  filesystem it is the same file as `SKILL.md`.

## Sweeping

A sweep's zero counts only once its pattern has found one known hit.

- List the surfaces before the spellings: the tracked tree, untracked files,
  other checkouts, every memory pool, issue and pull request bodies.
- Sweep a hyphenated name as `<a>[ _-]<b>` case-insensitively, and a moved
  rule by its vocabulary, since a move rewords it.
- Re-read each edited file top to bottom, because the survivor sits nearest
  the correction; grep a changed signature tree-wide as `fn(`.

## Frontmatter

- `name`: the directory's name. A skill the model loads takes the gerund
  form, verb plus object (`updating-wiki-pages`); one a person types keeps the
  voice of its pool.
- `description`: one `Use when …` sentence that classifies the situation
  without restating the body, in the third person, with no list of typed words
  and no angle brackets: the listing truncates long entries and drops the
  least-used first. A `Not for …` clause names the sibling that could claim
  the same request, because negative scope stops over-triggering and more
  positive description does not. `plugin eval` overstates firing: count
  Skill calls in live `claude -p --output-format stream-json` runs.
- `disable-model-invocation: true` on a skill only a person types: a command
  is an order given, not an operation offered. Its `description` says what
  it does, since no model chooses it by the situation.
- `user-invocable: false` on a skill only the model loads: it leaves the `/` menu.
- A skill a person types takes free-form text: it finds what it needs (a url,
  a name, a goal) anywhere in the text, asks for what is missing, and never
  refuses for wording, because a person does not remember a grammar. Its
  `argument-hint` is a plain example, not a grammar.

## Body

Zero to three sections, ordered so the reader meets each when it applies,
shaped to their material:

| the material | the shape |
| --- | --- |
| a subject that reduces to a small rule | the rule, from first principles |
| a subject thick with exceptions | a few worked examples that carry the shape |
| a term the skill encapsulates | its definition |
| distinct situations | a catalogue: the situation in one column, the action it selects in the next |

A catalogue row that selects a whole mode links a file in `references/`: the
row keeps the selector, the file keeps the body. A reference no row names is
never read, and one over 100 lines opens with a summary.

Split by the trigger, not by the content: variants of one situation of use,
one `description`, stay one skill with each variant a part in `references/`;
situations that read clearer as separate descriptions are separate skills.

An entry skill exists only for work started on purpose, by a person handing
work to an agent or one agent to another, as `kickoff` is; a plugin whose
skills each trigger on their own situation has none, as mumu-verification's `spec`,
`test` and `eval` do. An entry skill is a router: its `SKILL.md` is a routing
table, each row a situation in the words a person or a task would use and the
playbook in `references/` it opens, tried in order with a fallback row last;
the agent matches one row and copies that playbook's steps verbatim into its
todo list, a step not done staying as `skip: <reason>`. Copied steps are the
ones done, where a paraphrase drops them. A check every playbook needs runs
after the match, before the first step, and a step cited from another playbook
is named with it (`Lead 4`). A playbook links documents by relative path and
runs a script by `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/scripts/<name>`, because
a command runs from any directory.

## Register

Cut a rule before you shorten it: compliance falls with the number of rules
held at once. Plain imperatives, no capitals and no `MUST`; keep a prohibition
a prohibition. One term per concept, no dates or versions, no constant without
the reason for its value. An example that repeats its instruction anchors the
agent to the sample instead of the rule.

- Write a rule's consumer in the same change, with hostile cases, and
  compress a rule clause by clause against the original.
- A replacement rule gets a forward pass, what it now refuses, and a backward
  pass, what leaned on the old shape; a rule stated twice is fixed twice.

A vendored skill is a byte-identical copy of its upstream, named on the first
line of its body: an upgrade replaces the whole file, and any edit breaks that
identity.

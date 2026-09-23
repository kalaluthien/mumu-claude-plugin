# Skills and agents

Write only what the reader cannot derive: house conventions, defaults that
surprise, values that must match another file. An `agents/*.md` file takes a
skill's frontmatter rules; its body is the delegate's system prompt.

## Frontmatter

- `name`: the directory's name. A skill the model loads takes the gerund
  form, verb plus object (`updating-wiki-pages`); one a person types keeps the
  voice of its pool.
- `description`: one `Use when …` sentence that classifies the situation
  without restating the body, in the third person, with no list of typed words
  and no angle brackets: the listing truncates long entries and drops the
  least-used first. A `Not for …` clause names the sibling that could claim
  the same request, because negative scope stops over-triggering and more
  positive description does not.
- `disable-model-invocation: true` on a skill only a person types: a command
  is an order given, not an operation offered.

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

State a finished state as a predicate the agent can check, never an
adjective. Name the failure modes that raise no error.

Compaction keeps only the body's opening, so a rule that must survive a long
session sits near the top.

## Register

Cut a rule before you shorten it: compliance falls with the number of rules
held at once. Plain imperatives, no capitals and no `MUST`; keep a prohibition
a prohibition. One term per concept, no dates or versions, no constant without
the reason for its value. An example that repeats its instruction anchors the
agent to the sample instead of the rule.

A vendored skill is a byte-identical copy of its upstream, named on the first
line of its body: an upgrade replaces the whole file, and any edit breaks that
identity.

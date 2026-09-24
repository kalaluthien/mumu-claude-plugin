# Scripts and hooks

A script is a mechanism a caller trusts without reading, and a mechanised rule
fails silently where a written one fails loudly.

A lesson filed here becomes a script or hook with its failing case, and
nothing is filed in memory.

## Name, place, contract

- The extension carries the language, `.py` or `.sh`, so a glob can select by
  it. A script a flow asks a question is `<subject>-<question>`; one git or the
  harness runs unasked is `<verb>-<object>`. No state, verdict or measurement
  in the name.
- It lives in the owning skill's `scripts/`, so it goes with the procedure
  that reaches it. A top-level `scripts/` holds what has no owner: one a hook
  or CI runs, one two skills call.
- The line under the shebang states its purpose. It handles its own errors
  and assumes no tool is installed.
- One script answers one question. A sequence with judgement is a skill, one
  without is a script, a judgement with no sequence is a sentence. Never write
  a second reader of a rule another script owns.

## Exit status

- A harness hook: 0 allows, 2 refuses with the reason on stderr, no other code
  blocks. For more than allow-or-refuse, exit 0 with JSON under
  `hookSpecificOutput`; exit 2 overrides that JSON, so never write both.
- A git hook: git blocks on any non-zero, so the docstring names the codes the
  script uses.
- A script that answers a question prints the answer as a word and exits 0;
  the caller reads the word. Non-zero means *I could not look*.

A guard's own crash permits and names itself, so a bug in the check costs one
unjudged call, not a wall across everything it guards.

Four harness facts, each of which makes a hook misfire when missed:

- Exit 2 blocks only on events that can block; on `PostToolUse`,
  `SessionStart`, `Notification` and their kind it prints and execution goes on.
- On `SessionStart` and `UserPromptSubmit` stdout reaches the model only on
  exit 0, so a script that announces always exits 0.
- A `PreToolUse` matcher lists tool names; a call to a tool it does not name
  is never seen.
- `SessionStart` fires again after `/clear` and each compaction, its `source`
  saying which, and `SessionEnd` never fires on `kill -9`.

## Readers

A reader answering from the wrong line or from silence looks like a pass.

- A missing directory is a refusal, not an empty result; an absence that one
  reading cannot tell from a pass refuses, with an explicit override.
- Answer yes, no or *could not look*, each its own override: a second reader
  whose no-match branch is silence goes stale unseen.
- Anchor on the line printed for the fact itself, before any optional step,
  matched by equality: a grep for a literal also matches its own definition.
- The producer and the reader share the anchor by import; the case spells it
  separately, so a drift in either fails.
- Check the shape of what a parser returns: `json.loads` and
  `ast.literal_eval` return any value, not the dict you expect.
- Probe a predicate over where an effect lands once per form that moves it:
  subshell, pipeline, `&`, `-c` string, heredoc, `pushd`.
- `git diff --cached --name-only` names only a rename's destination; pass
  `--no-renames`.
- Print what was read, from where, and which branch was taken.
- Give a polling loop a terminal branch: for a finished subject, absence is
  the steady state.

## Widening a guard

A guard patched one exhibit at a time keeps the route nobody showed.

- Before the branch, state the bad state and list every route to it: each
  verb, the REST and GraphQL calls, a variable or `xargs` spelling.
- When a finding's fix is a new branch in the code the last fix added,
  withdraw the mechanism: allow-list the forms it can read, over raw text.
- A new rule applies at every site that decides the same question, one case
  per site; a set spelled twice drifts, so name it once.
- Before an allow-list replaces a deny-list, diff both over the same tree, and
  count what an "I cannot judge" branch turns off over the real record.
- A git hook reaches every worktree of the clone, and a changed allowance
  breaks other suites' fixtures: run every suite, then read CI for the sha.

## Verifying one

A guard you did not watch refuse is not verified. Break each branch
separately, watch its named check fail, restore by undoing that one edit, and
assert on what the break changes, never on an exit status alone: a crash and a
refusal share one. Beside every refusal branch put named allow cases for the
ordinary neighbours — the next directory, the read-only verb, the quoted
string that only mentions the guarded phrase — because a suite of refusals
stays green while the guard refuses too much.

A clean `git merge` runs no `pre-commit`, so drive a git hook with
`git commit`; drive a harness hook in a real run of `claude -p --settings
<json>`, which adds it beside the global hooks.

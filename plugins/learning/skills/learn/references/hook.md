# Scripts and hooks

A script is a mechanism a caller trusts without reading, and a mechanised rule
fails silently where a written one fails loudly.

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

Three harness facts, each of which makes a hook enforce nothing when missed:

- Exit 2 blocks only on events that can block; on `PostToolUse`,
  `SessionStart`, `Notification` and their kind it prints and execution goes on.
- On `SessionStart` and `UserPromptSubmit` stdout reaches the model only on
  exit 0, so a script that announces always exits 0.
- A `PreToolUse` matcher lists tool names; a call to a tool it does not name
  is never seen.

## Absence

A stale input arrives as an absence that looks like a pass.

- A missing directory is a refusal, not an empty result.
- Print what was read, from where, and which branch was taken.
- Give a polling loop a terminal branch: for a finished subject, absence is
  the steady state.

## Verifying one

A guard you did not watch refuse is not verified. Break each branch
separately, watch its named check fail, restore by undoing that one edit, and
assert on what the break changes, never on an exit status alone: a crash and a
refusal share one. Beside every refusal branch put named allow cases for the
ordinary neighbours — the next directory, the read-only verb, the quoted
string that only mentions the guarded phrase — because a suite of refusals
stays green while the guard refuses too much.

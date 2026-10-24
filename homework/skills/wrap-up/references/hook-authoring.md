# Hook authoring

Write or edit a hook or a script so it fails where a rule breaks, with the case it must fail on.

A script is a mechanism a caller trusts without reading, and a mechanised rule fails silently where a written one fails loudly. A lesson filed here becomes a script or hook with its failing case, and nothing is filed in memory.

## Domain

- **Placement**: where it sits and how it is named: the repository's `AGENTS.md`.
- **Purpose line**: the line under the shebang states its purpose. It handles its own errors and assumes no tool is installed.
- **One question**: one script answers one question: a sequence with judgement is a skill, one without is a script. Never write a second reader of a rule another script owns.
- **Exit codes**: a harness hook exits 0 to allow and 2 to refuse, the reason on stderr; for more, exit 0 with JSON under `hookSpecificOutput`, never both. A git hook blocks on any non-zero, so its docstring names its codes. A script that answers prints the answer as a word and exits 0; non-zero means *I could not look*.
- **Crash permits**: a guard's own crash permits and names itself, so a bug costs one unjudged call, not a wall across everything it guards.
- **Event limits**: exit 2 blocks only on events that can block; stdout reaches the model on `SessionStart` and `UserPromptSubmit` only at exit 0; a `PreToolUse` matcher never sees a tool it does not name; `SessionStart` fires again after each compaction, and `SessionEnd` never fires on `kill -9`.

## Readers

A reader answering from the wrong line or from silence looks like a pass.

- **Could not look**: a missing directory is a refusal, not an empty result. Answer yes, no or *could not look*, each its own branch: a no-match branch that is silence goes stale unseen.
- **Anchor**: anchor on the line printed for the fact itself, matched by equality: a grep for a literal also matches its own definition. The producer and the reader share the anchor by import; the test spells it separately.
- **Shape**: check the shape of what a parser returns, and pass `--no-renames` to a diff whose names you read.
- **Every form**: probe a predicate over where an effect lands once per form that moves it: subshell, pipeline, background job, heredoc.
- **Trace**: print what was read, from where, and which branch was taken; give a polling loop a terminal branch.

## Widening a guard

A guard patched one exhibit at a time keeps the route nobody showed.

- **Every route**: before the branch, state the bad state and list every route to it: each verb, the REST and GraphQL calls, a variable spelling.
- **Withdraw**: when a finding's fix is a new branch in the code the last fix added, withdraw the mechanism: allow-list the forms it can read, over raw text.
- **Every site**: a new rule applies at every site that decides the same question, one case per site, the set named once.
- **Diff both lists**: before an allow-list replaces a deny-list, diff both over the same tree, and count what an "I cannot judge" branch turns off over the real record.
- **Every worktree**: a git hook reaches every worktree of the clone: run every suite, then read CI for the sha.

## Steps

**Watch it refuse**: a guard you did not watch refuse is not verified. Break each branch separately, watch its named check fail, restore by undoing that one edit, and assert on what the break changes, never on an exit status alone. Beside every refusal put named allow cases for its ordinary neighbours, because a suite of refusals stays green while the guard refuses too much. Drive a git hook with `git commit`, since a clean merge runs none, and a harness hook in a real `claude -p --settings <json>` run.

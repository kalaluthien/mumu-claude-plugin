# Harness authoring

Write or edit a skill, an agent file, a hook or a script, so its reader follows it on the first read and a rule a check can decide fails where it breaks.

## Domain

- **Underivable only**: write only what the reader cannot derive: house conventions, defaults that surprise, values that must match another file. An `agents/*.md` file takes a skill's frontmatter rules; its body is the delegate's system prompt.
- **Lesson filed**: a procedure belongs to the skill that owns the work, edited in its source, never in the plugin cache, else a new skill in `~/.claude/skills/`, as the steps as run with what varied as parameters; how a delegate should work, to its `agents/<name>.md`; a rule a check can decide, to a script or hook with its failing case, and nothing is filed in memory.
- **Trusted mechanism**: a script is a mechanism a caller trusts without reading, and a mechanised rule fails silently where a written one fails loudly.
- **Placement**: where each file sits, how it is named and how one links another: the repository's `AGENTS.md`.
- **Delegates**: a delegate's report is its final message, never a file it writes: the brief asks for it so. A slash command in a delegate's prompt is plain text: the brief names the skill for it to call.
- **Purpose line**: the line under a script's shebang states its purpose. It handles its own errors and assumes no tool is installed.
- **One question**: one script answers one question: a sequence with judgement is a skill, one without is a script. Never write a second reader of a rule another script owns.
- **Exit codes**: a harness hook exits 0 to allow and 2 to refuse, the reason on stderr; for more, exit 0 with JSON under `hookSpecificOutput`, never both. A git hook blocks on any non-zero, so its docstring names its codes. A script that answers prints the answer as a word and exits 0; non-zero means *I could not look*.
- **Crash permits**: a guard's own crash permits and names itself, so a bug costs one unjudged call, not a wall across everything it guards.
- **Event limits**: exit 2 blocks only on events that can block; stdout reaches the model on `SessionStart` and `UserPromptSubmit` only at exit 0; a `PreToolUse` matcher never sees a tool it does not name; `SessionStart` fires again after each compaction, and `SessionEnd` never fires on `kill -9`. A plugin monitor is never restarted in a session once it dies: `/reload-plugins` leaves a running one as it is, and `when: on-skill-invoke` starts it on the skill's first run only.

## Steps

1. **Place**: put the file where the repository's `AGENTS.md` says. A skill folder has no `skill.md` in any case, since on a case-insensitive filesystem it is `SKILL.md`.
2. **Write a skill**: follow Skill below. A directory marketplace loads plugins from its checkout, so a pulled merge needs no update and a worktree's edit reaches no session.
3. **Write a hook or script**: follow Hook below, the reader and guard rules first.
4. **Move**: `git mv`, then search the plugin and its checks for the old path and bare name until none is stale, and open each new link once. A stale path fails only when that step runs. A moved rule is re-derived against each member of its new home, and the old home emptied only once a grep of the destination finds the rule's nouns. Moving a plugin folder: remove the empty `<new>-inline` data folders a `--plugin-dir` probe leaves before moving `~/.claude/plugins/data/<old>-*`, since `mv` into an existing folder nests; uninstall the old plugin only with `--keep-data`; after the pull an old folder can survive holding untracked `__pycache__`, so `ln -s` nests the link inside it: check `readlink` of each bridge, never `ls -l` alone. A deleted script a git hook calls breaks every commit until the hook goes. Mark a criterion on live state "at cutover" and post its output after the merge.
5. **Sweep**: a sweep's zero counts only once its pattern has found one known hit. List the surfaces first: the tracked tree, untracked files, other checkouts, every memory pool, issue and pull request bodies. Sweep a hyphenated name with any separator and any case, and a moved rule by its vocabulary. Re-read each edited file top to bottom, since the survivor sits nearest the correction.
6. **Watch it refuse**: a guard you did not watch refuse is not verified. Break each branch separately, watch its named check fail, restore by undoing that one edit, and assert on what the break changes, never on an exit status alone. Beside every refusal put named allow cases for its ordinary neighbours, because a suite of refusals stays green while the guard refuses too much. Drive a git hook with `git commit`, since a clean merge runs none, and a harness hook in a real `claude -p --settings <json>` run; [harness-probes.md](harness-probes.md) says how to probe a hook, skill, monitor or session flow and how to backtest on past transcripts.

## Rules

### Skill

- **`name`**: the directory's name, a gerund with its object when the model loads it.
- **`description`**: one `Use when …` sentence that classifies the situation without restating the body, in the third person, with no list of typed words and no angle brackets, since the listing truncates. A `Not for …` clause names the sibling that could claim the same request, because negative scope stops over-triggering and more positive description does not. Count firing in live `claude -p --output-format stream-json` runs, since `plugin eval` overstates it; run eval cases by [harness-probes.md](harness-probes.md).
- **Invocation**: `disable-model-invocation: true` on a skill only a person types, its description saying what it does; `user-invocable: false` on one only the model loads. A slash command only a person types is not out of reach under herdr: `herdr agent prompt $HERDR_PANE_ID "/<command> <args>"` sends it to the session's own pane; ask the person only when `HERDR_PANE_ID` is unset or the prompt is refused.
- **Unread keys**: a key the build does not read is accepted in silence: confirm a key by what the session's skill list shows, never by the absence of an error.
- **Not yours**: a skill whose file is not yours to edit: a `Skill(<name>)` deny rule in a settings file stops the model's call only; the typed form still runs.
- **Free-form text**: a skill a person types takes free-form text: it finds what it needs anywhere in it, asks for what is missing, and never refuses for wording; its `argument-hint` is a plain example, not a grammar.
- **Sections**: zero to three sections, ordered so the reader meets each when it applies. Use a small rule from first principles, a few worked examples for a subject thick with exceptions, a definition for a term, or a catalogue (the situation in one column, the action in the next) for distinct situations. A row that selects a whole mode links a file in `references/`; a reference no row names is never read, and one over 100 lines opens with a summary.
- **By trigger**: split by the trigger, not by the content: variants of one situation stay one skill, each variant a reference.
- **Entry skill**: an entry skill exists only for work started on purpose, a person or an agent handing work over. Its `SKILL.md` is a routing table, each row a situation in the words a person would use and its playbook, tried in order with a fallback row last. The agent copies that playbook's steps verbatim into its todo list, because a paraphrase drops them. A check every playbook needs runs after the match, and a step cited from another playbook is named with it.
- **Batches**: a skill that asks the owner in batches loops within the same call until nothing is left but what the owner rejected, never deferring the rest to a next run, because the owner invoked it to finish the job.
- **Cut first**: cut a rule before you shorten it: compliance falls with the number of rules held at once. Plain imperatives, no capitals; keep a prohibition a prohibition. One term per concept, no dates or versions, no constant without the reason for its value. An example that repeats its instruction anchors the agent to the sample instead of the rule.
- **Consumer**: write a rule's consumer in the same change, with hostile cases.
- **Conditional rules**: a conditional rule loads when the agent opens a matching file with `Read`, never on a write or a shell read: scope it to paths the agent will open.
- **Replacement rules**: a replacement rule gets a forward pass, what it now refuses, and a backward pass, what leaned on the old shape; a rule stated twice is fixed twice.
- **Vendored**: a vendored skill is a byte-identical copy of its upstream, named on the first line of its body, so an upgrade replaces the whole file.

### Hook

A reader answering from the wrong line or from silence looks like a pass.

- **Could not look**: a missing directory is a refusal, not an empty result. Answer yes, no or *could not look*, each its own branch: a no-match branch that is silence goes stale unseen.
- **Anchor**: anchor on the line printed for the fact itself, matched by equality: a grep for a literal also matches its own definition. The producer and the reader share the anchor by import; the test spells it separately.
- **Shape**: check the shape of what a parser returns, and pass `--no-renames` to a diff whose names you read.
- **Every form**: probe a predicate over where an effect lands once per form that moves it: subshell, pipeline, background job, heredoc.
- **Trace**: print what was read, from where, and which branch was taken; give a polling loop a terminal branch.

A guard patched one exhibit at a time keeps the route nobody showed.

- **Every route**: before the branch, state the bad state and list every route to it: each verb, the REST and GraphQL calls, a variable spelling.
- **Withdraw**: when a finding's fix is a new branch in the code the last fix added, withdraw the mechanism: allow-list the forms it can read, over raw text.
- **Every site**: a new rule applies at every site that decides the same question, one case per site, the set named once.
- **Diff both lists**: before an allow-list replaces a deny-list, diff both over the same tree, and count what an "I cannot judge" branch turns off over the real record.
- **Every worktree**: a git hook reaches every worktree of the clone: run every suite, then read CI for the sha.

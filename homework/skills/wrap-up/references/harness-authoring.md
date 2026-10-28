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
- **Event limits**: exit 2 blocks only on events that can block; stdout reaches the model on `SessionStart` and `UserPromptSubmit` only at exit 0; a `PreToolUse` matcher never sees a tool it does not name; `SessionStart` fires again after each compaction, and `SessionEnd` never fires on `kill -9`; a plugin monitor is never restarted once it dies, `/reload-plugins` leaves a running one as it is, and it starts at session start with `when: always` but on the skill's first run only with `when: on-skill-invoke`.

## Steps

1. **Place**: put the file where the repository's `AGENTS.md` says. A skill folder has no `skill.md` in any case, since on a case-insensitive filesystem it is `SKILL.md`.
2. **Write a skill**: follow Skill below. A directory marketplace loads plugins from its checkout, so a pulled merge needs no update and a worktree's edit reaches no session.
3. **Write a hook or script**: follow Hook below, the reader and guard rules first.
4. **Move**: `git mv`, then search the plugin and its checks for the old path and bare name until none is stale, and open each new link once. A stale path fails only when that step runs.
   - **Moved rule**: re-derive it against each member of its new home; empty the old home only once a grep of the destination finds the rule's nouns.
   - **Moved plugin folder**: it moves its data folder too. Remove the empty `<new>-inline` folders a `--plugin-dir` probe leaves first, since `mv` into an existing folder nests.
   - **Uninstall**: the old plugin only with `--keep-data`.
   - **Bridge symlink**: check `readlink` of each, never `ls -l` alone; an old folder holding untracked `__pycache__` nests the link.
   - **Hook script**: a deleted script a git hook calls breaks every commit.
   - **Cutover**: mark a criterion on live state "at cutover" and post its output after the merge.
5. **Sweep**: a sweep's zero counts only once its pattern has found one known hit. List the surfaces first: the tracked tree, untracked files, other checkouts, every memory pool, issue and pull request bodies. Sweep a hyphenated name with any separator and any case, and a moved rule by its vocabulary. Re-read each edited file top to bottom, since the survivor sits nearest the correction.
6. **Watch it refuse**: a guard you did not watch refuse is not verified. Break each branch separately, watch its named check fail, restore by undoing that one edit, and assert on what the break changes, never on an exit status alone. Beside every refusal put named allow cases for its ordinary neighbours, because a suite of refusals stays green while the guard refuses too much. Drive a git hook with `git commit`, since a clean merge runs none. Drive a harness hook, skill or monitor in a real session, and measure on the record it leaves:
   - **Hook in `claude -p`**: in a scratch git folder, with the plugin copied to the scratchpad.
     - **Run**: `claude -p "<prompt>" --plugin-dir <copy> --model haiku --output-format json` with the herdr variables and `CLAUDECODE` unset; a same-named plugin replaces the installed one. A copied `CLAUDE_CONFIG_DIR` starts `Not logged in`.
     - **Count**: change state, `--resume <id>`, count the `hook_additional_context` attachments in the transcript; match paths resolved and as spelled (`/var` is `/private/var`).
     - **Skills**: under `-p` a refused typed command prints nothing: read the `Skill` `tool_result` from `--output-format stream-json --verbose --max-turns 2`, and the skill list from the `init` line (`.type=="system" and .subtype=="init"`; `.type=="system"` alone also matches hook messages).
     - **Auto mode**: needs `--model sonnet`, since on haiku it is off and every command reads `requires approval`; run a control with no deny first.
     - **Classifier**: to test a hook `allow`, add `--setting-sources project,local` and `--settings '{"autoMode":{"hard_deny":["$defaults","Never run <cmd>"]}}'`.
   - **Interactive tab**: for a flow `-p` cannot reach (handoff, start-up, monitor, pane), since a `-p` child of a manager's pane takes itself for the manager.
     - **Start**: in a folder that enables the plugins and sets no `agent`, or with `--plugin-dir <worktree plugin>` and no settings file; confirm the skill is listed first.
     - **Trust dialog**: `herdr agent start` answers `agent_not_ready`; `send-keys` down and enter.
     - **Setup**: pass your own workspace and a fresh agent name; set env by `pane send-text`, since `agent start` env never reaches the pane's shell.
     - **Mode**: add `--permission-mode default` or no tool prompt shows; make the agent busy by a long reply, since a foreground `sleep` is refused.
     - **Slash command**: a `herdr agent prompt` slash command does not run; type `/reload-plugins` by `pane send-text`, then `send-keys enter`.
     - **Quit**: `/exit`, one more `enter` for the stop-background-work dialog, then `herdr tab close`. Stage files by name, never `git add -A`, since a `--plugin-dir` tab writes an untracked file into the plugin.
     - **Refused**: auto mode refuses editing a probe's transcript, keys or reads sent to a probe, and a fan-out of `claude -p`: write a scratchpad script and hand the owner `! bash <path>`.
   - **Baseline**: before blaming a change, run the same command on `git archive <sha> <plugin> | tar -x -C <scratch>` beside head, which compares head against the merge base (`git merge-base HEAD origin/main`), never the moving `origin/main`.
   - **Past transcripts**: to tune or measure a hook or trigger on `~/.claude/projects/*/*.jsonl`.
     - **Sessions**: count top-level interactive ones (`entrypoint` not `sdk*`, with a stop entry); subagents sit in subfolders; `agent-setting`, else `sdk-cli`, marks headless.
     - **Replay**: cut at each event's byte offset with a fresh `CLAUDE_PLUGIN_DATA`; skip and count missing files.
     - **Sample**: per band of tool calls; tune on one hash half and score the other.
     - **Labels**: a first prompt is a launch prompt and says nothing; give a timeline without call counts and read the boundary rows yourself.
     - **Dating**: transcripts are the only record of a guard's refusals; date a lesson by the first Write or Edit of its path, since a file's mtime may come from a batch touch.
     - **Changed files**: add the diff of each `pr-link` record's PR whose head branch is the session's `agent-name`, since Edit and Write miss Bash edits; check first that `pr-link` records exist.

## Rules

### Skill

- **`name`**: the directory's name, a gerund with its object when the model loads it.
- **`description`**: one `Use when …` sentence that classifies the situation without restating the body, in the third person, with no list of typed words and no angle brackets, since the listing truncates. A `Not for …` clause names the sibling that could claim the same request, because negative scope stops over-triggering and more positive description does not.
- **Eval case**: count firing in live `claude -p --output-format stream-json` runs, since `plugin eval` overstates it; a `claude plugin eval` case has these limits:
  - **Grants and scoring**: Bash and Write need `--allow-tools Bash Write`, else a `tool_used: Bash` or path grader scores 0 on main too; a reply-only llm grader cannot see a code total; a grader path with `..` is refused. Probe a grader `pattern` with Python `re.search`, never `grep -E`; a `'` inside a single-quoted YAML pattern fails the case load; a judge at `effort: low` skipped per-criterion rules.
  - **Role**: there is no agent field: put the role in `append_system_prompt`, which replaces the agent body, so a case needing the body's paths cannot pass honestly.
  - **Scaffold**: `--scaffold` is off and skipped silently, and the child cannot read the config, so grade the attempt (`tool_used`, `input_match`), not its result.
  - **Fields**: a `prompt.md` case has no `scaffold_script`; its `env` takes only `EVAL_*`.
  - **Prompt**: a `disable-model-invocation` skill loads only on its slash line; a prompt shaped unlike what the start script sends fails the case.
  - **Sandbox**: it refuses creating `.git` (seed a plain folder, `git grep --no-index`) and headless Chrome; a child that launches a subagent runs it in the foreground and replies once the file exists.
  - **Timing and repeats**: give a background run a timeout of at least twice its run time. A script that reads live transcripts differs run to run and guards nothing; a hook is deterministic on its `fixtures/*.jsonl` with `CLAUDE_PLUGIN_DATA` a temp folder and `cwd` a git root.
- **Invocation**: `disable-model-invocation: true` on a skill only a person types, its description saying what it does; `user-invocable: false` on one only the model loads.
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

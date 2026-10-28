# Harness probes

Test a hook, skill, monitor, eval case or session-level flow in a real session, or tune a hook on past transcripts, so a claim about the harness rests on a run that can fail.

## Domain

- **Hook probe**: a headless `claude -p` run in a scratch git folder; it reaches a mechanical hook, not a flow that needs a live terminal.
- **Session probe**: a separate interactive session in its own terminal tab; it reaches what a hook or `-p` cannot: a handoff, a start-up flow, a monitor, a pane.
- **Transcript**: `~/.claude/projects/*/<session id>.jsonl`; subagents sit in subfolders.

## Steps

1. **Hook probe**: copy the plugin to the scratchpad and run `claude -p "<prompt>" --plugin-dir <copy> --model haiku --output-format json` with the herdr variables and `CLAUDECODE` removed from the env. Take `session_id`, change state, run `--resume <id>`, then count the `"type": "hook_additional_context"` attachments in the transcript. Match paths resolved and as spelled (`/var` is `/private/var` on macOS).
2. **Session probe**: pick a folder whose `.claude/settings.local.json` enables the plugins and sets no `agent`, or pass `--plugin-dir <worktree plugin>`; confirm the skill is listed. Start it in a new tab (`herdr tab create --cwd <dir> --no-focus`, then `herdr agent start <name> --kind claude --pane <pane> -- ...`), because a `claude -p` child of a manager's pane takes itself for the manager even with the session variables removed.
3. **Close**: quit a probe with `/exit`, `enter` and one more `enter` for the stop-background-work dialog, since Ctrl+C leaves it running; then `herdr tab close <tab_id>`.
4. **Backtest**: replay a Stop hook by cutting a transcript at each stop's byte offset and running the real hook on the prefix with a fresh `CLAUDE_PLUGIN_DATA`, as `hooks/replay-score.py` does. Sample per band of tool calls (20 each of 0-15, 15-40, 40-80, 80-160, 160+) so short sessions are not swamped, tune on one hash half and score the other, and replay at the lesson threshold's ceiling for the worst case.
5. **Changed files**: to count which files a session changed, add the diff (`gh pr diff`) of each `{"type":"pr-link","prUrl":...}` record whose PR head branch equals the session's `agent-name`, since a worker edits through Bash and Edit and Write calls alone miss it. Check first that the transcripts still carry `pr-link` records.

## Rules

### Hook probe

- **Replace by name**: `--plugin-dir <dir>` whose plugin has an installed plugin's name replaces it for that session.
- **Auto mode**: a probe under `--permission-mode auto` needs `--model sonnet`; on haiku auto mode is off and every command reads `This command requires approval`. Run a control with no deny first. To test a hook `allow` against the classifier, add `--setting-sources project,local` and `--settings '{"autoMode":{"hard_deny":["$defaults","Never run <cmd>"]}}'`.
- **Hide user skills**: `--settings '{"skillOverrides":{"<skill>":"off"}}'`; plugin skills, user settings and the login stay. A copied `CLAUDE_CONFIG_DIR` starts `Not logged in`, and copying `~/.claude.json` in is refused.
- **Invocation keys**: under `-p` a refused typed `/plugin:skill` prints nothing; read the `Skill` `tool_use` and `tool_result` from `--output-format stream-json --verbose --max-turns 2`. The refusal text shows only in a live tab.
- **Skill list**: `jq -r 'select(.type=="system" and .subtype=="init")|.skills[]'`; `.type=="system"` alone also matches hook messages, which carry no `.skills`.
- **Fan-out refused**: a harness that fans out many `claude -p` builds is refused as unsafe agent creation: write it, then hand the owner one `!` command that runs it in the background.

### Session probe

- **Trust dialog**: a new folder opens on it and `herdr agent start` answers `agent_not_ready`: read the pane, then `herdr pane send-keys <pane> down` and `enter`, lowercase.
- **Own workspace**: pass your own `--workspace` to `tab create`, else the tab lands in the owner's focused one; `tab create` returns the pane at `.result.root_pane.pane_id`.
- **Env**: env set on `herdr agent start` never reaches the pane's shell; `pane send-text "export K=V"` then `enter` first.
- **Names**: each start needs a new agent name (`agent_name_taken`), lowercase, no colon.
- **Permission mode**: a probe inherits auto mode, so no tool prompt shows; pass `-- --model haiku --permission-mode default` to reach `blocked`. A foreground `sleep N` is refused by the Bash hook: make the agent busy with a long reply.
- **Artifact route**: a `-p` child has no `Artifact` tool; use a tab. There the harness calls `quickstart` before any skill loads, so a skip must sit in the skill's description. Each probe publishes a private artifact: list its id for the owner.
- **Transcript edits refused**: auto mode refuses appending an entry to a probe's transcript, and `send-keys` or reads on a probe started with a dropped tool grant: write the step as a scratchpad script and hand the owner `! bash <path>` at once.
- **Untracked files**: a tab started with `--plugin-dir <worktree>/<plugin>` may write an untracked `tsconfig.json`; stage files by name, never `git add -A`.
- **Reload**: `/reload-plugins` leaves a running monitor on the same pid, and a `herdr agent prompt` slash command does not run; type it by `pane send-text`, then `send-keys enter`. Find the monitor by `ps aux | grep <copy>/monitors`.

### Backtest

- **Missing files**: transcripts vanish within days; skip and count the missing ones, or the replay crashes.
- **Opening prompt**: almost every session opens with a start-up prompt, so a first prompt says nothing; show its command arguments and later user words, and drop `<task-notification>` lines.
- **Labels**: labellers shown tool-call counts label by them, so tuning a call-count trigger on those labels is circular; give a timeline of user words, calls, errors and replies with no counts, and read the boundary rows yourself.
- **Gaps**: a window can hold few active days; a memory file's mtime may be a batch touch, so date a lesson by the first Write or Edit of its path; a guard that logs no refusal leaves only transcripts as its record.

### Eval cases

- **Grants**: `claude plugin eval` withholds Bash and Write unless `--allow-tools Bash Write` grants them, so a `tool_used: Bash` or path grader scores 0 on main too. A reply-only llm grader cannot see a code total.
- **Role**: there is no agent field; put the role in `execution.append_system_prompt` of `case.yaml`. The text replaces the agent body, so a case needing the body's paths cannot pass honestly.
- **Scaffold**: `--scaffold` is off by default and skipped silently. The script runs in `<tmp>/home/cwd` with `HOME=<tmp>/home` and no `CLAUDE_CONFIG_DIR`, so the child cannot read the config: grade the attempt (`tool_used`, `input_match`), not its result. A `prompt.md` case admits no `scaffold_script`; `env` takes only `EVAL_*`; a grader path with `..` is refused.
- **Sandbox**: it refuses creating `.git` (seed a plain folder, `git grep --no-index`) and starting headless Chrome. A child that launches a subagent must run it in the foreground and reply once the file exists.
- **Slash-only skill**: a `disable-model-invocation` skill loads only on its slash line: open the prompt with that line, then the scenario. A prompt shaped unlike what the start script sends fails the case.
- **Pattern**: probe a grader `pattern` with Python `re.search`, never `grep -E` (`[^\n]` excludes the letter n there). A `'` inside a single-quoted YAML pattern fails the case load. A judge at `effort: low` skipped per-criterion rules in half the runs.
- **Baseline**: before blaming a change, run the same command on `git archive <sha> <plugin> | tar -x -C <scratch>` beside head, in parallel. Compare head with `--ref "$(git merge-base HEAD origin/main)"`, never `origin/main`, which moves when another PR merges.
- **Deterministic only**: a script that reads live transcripts differs run to run and guards nothing; a hook is deterministic on its `fixtures/*.jsonl` with `CLAUDE_PLUGIN_DATA` a temp folder and `cwd` a git root.
- **Timeout**: give a background eval a `timeout` of at least twice its run time.

# homework

At a stop, homework's Stop hook asks the session to keep what it learned, and the `wrap-up` skill files each lesson where the next session will meet it.

## Turn the ask off

Set `HOMEWORK_WRAP_UP=off` in the environment Claude Code starts with, or in the `env` of a settings file, such as a repository's `.claude/settings.local.json`:

```json
{ "env": { "HOMEWORK_WRAP_UP": "off" } }
```

The hook then neither asks nor writes; a person can still ask for a retro.

The variable was `WRAP_UP`, and so was `WRAP_UP_THRESHOLD` for the threshold, before the rename to `HOMEWORK_WRAP_UP` and `HOMEWORK_WRAP_UP_THRESHOLD`; the old names do nothing now.

## Share memory across projects

Set one auto-memory folder for every session in `~/.claude/settings.json`; the retro and dream scripts fail with a message naming it until you do:

```json
{ "autoMemoryDirectory": "~/.claude/memory" }
```

Its `MEMORY.md` then loads in every session, and a SessionStart hook sends each lesson to it and prints the index of the repository's rare folder, `~/.claude/memory/<repo>/`, kept only for a lesson wrong or harmful outside that repository, where `<repo>` is the origin's name, else the checkout's folder name. Move a memory file between the two with `skills/wrap-up/scripts/move-memory.py <file> <folder>`.

## One count of the one memory home

The hook keeps the count of memory files changed since the last dream, and the lesson threshold, in `<autoMemoryDirectory>.wrap-up.json` beside the memory folder, so each plugin data folder reads the same count. `skills/wrap-up/scripts/list-unasked-sessions.py` lists, by cause, the sessions of 25 or more tool calls that the hook never asked: the hook is absent from their stop summaries where homework is not enabled for the project.

## Where a dream runs

In herdr, a dream without the `Workflow` tool runs in a Dreamer, a new tab named `<topic>-dreamer`, which `skills/wrap-up/scripts/start-dreamer.py` opens. The Dreamer asks you its questions there, reports, then runs `skills/wrap-up/scripts/close-dreamer.py`, which closes its own tab once the turn ends; run from any pane not named `*-dreamer`, that script closes nothing.

## What a wrap-up writes

- **Auto-memory**: written directly: a lesson in the folder `autoMemoryDirectory` names, and only one wrong or harmful outside its repository in that folder's `<repo>/`.
- **History**: every retro and dream records the memory folder in `<autoMemoryDirectory>.git`, a bare git directory beside it that no other repository reads or pushes; `git --git-dir ~/.claude/memory.git log -p` shows each lesson's changes; the history keeps a credential that was once written, so delete `~/.claude/memory.git` to purge it.
- **Skill lessons**: kept in memory, marked `skill:`, until a dream asks you whether to write each into its skill, keep it or drop it.
- **Anything else**: a lesson for `~/.claude/CLAUDE.md`, another repository's memory, a hook or a skill is written as a patch file; the wrap-up's report names the `! git -C <root> apply <patch file>` command that applies it, and nothing changes until you run it.
- **Hand-overs**: a wrap-up asks before it hands one over, and opens no GitHub issue for it.
- **Dream digests**: kept in the plugin's data folder, folders `0700` and files `0600`, with GitHub, Anthropic, OpenAI, Slack and AWS key-like strings masked.

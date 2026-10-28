# homework

At a stop, homework's Stop hook asks the session to keep what it learned, and the `wrap-up` skill files each lesson where the next session will meet it.

## Turn the ask off

Set `HOMEWORK_WRAP_UP=off` in the environment Claude Code starts with, or in the `env` of a settings file, such as a repository's `.claude/settings.local.json`:

```json
{ "env": { "HOMEWORK_WRAP_UP": "off" } }
```

The hook then neither asks nor writes to the plugin's data folder; a person can still ask for a retro, a dream or `dejavu`.

The variable was `WRAP_UP`, and so was `WRAP_UP_THRESHOLD` for the threshold, before the rename to `HOMEWORK_WRAP_UP` and `HOMEWORK_WRAP_UP_THRESHOLD`; the old names do nothing now.

## Share memory across projects

Set one auto-memory folder for every session in `~/.claude/settings.json`:

```json
{ "autoMemoryDirectory": "~/.claude/memory" }
```

Its `MEMORY.md` then loads in every session, and a SessionStart hook prints the index of the repository's own folder, `~/.claude/memory/<repo>/`, where `<repo>` is the origin's name, else the checkout's folder name. Move a memory file between the two with `skills/wrap-up/scripts/move-memory.py <file> <folder>`.

## What a wrap-up writes

- **Auto-memory**: written directly: a lesson for every project in the folder `autoMemoryDirectory` names, and a repository's lesson in that folder's `<repo>/`; with no `autoMemoryDirectory`, the project's own pool.
- **Skill lessons**: kept in memory, marked `skill:`, until a dream asks you whether to write each into its skill, keep it or drop it.
- **Anything else**: a lesson for `~/.claude/CLAUDE.md`, another repository's memory, a hook or a skill is written as a patch file; the wrap-up's report names the `! git -C <root> apply <patch file>` command that applies it, and nothing changes until you run it.
- **Issues**: a wrap-up asks before it files one.
- **dejavu digests**: kept in the plugin's data folder, folders `0700` and files `0600`, with GitHub, Anthropic, OpenAI, Slack and AWS key-like strings masked.

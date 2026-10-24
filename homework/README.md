# homework

At a stop, homework's Stop hook asks the session to keep what it learned, and the `wrap-up` skill files each lesson where the next session will meet it.

## Turn the ask off

Set `WRAP_UP=off` in the environment Claude Code starts with, or in the `env` of a settings file, such as a repository's `.claude/settings.local.json`:

```json
{ "env": { "WRAP_UP": "off" } }
```

The hook then neither asks nor writes to the plugin's data folder; a person can still ask for a retro, a dream or `dejavu`.

## What a wrap-up writes

- **This project's auto-memory**: written directly.
- **Anything else**: a lesson for `~/.claude/CLAUDE.md`, another project's memory, a hook or a skill is written as a patch file; the wrap-up's report names the `! git -C <root> apply <patch file>` command that applies it, and nothing changes until you run it.
- **Issues**: a wrap-up asks before it files one.
- **dejavu digests**: kept in the plugin's data folder, folders `0700` and files `0600`, with GitHub, Anthropic, OpenAI, Slack and AWS key-like strings masked.

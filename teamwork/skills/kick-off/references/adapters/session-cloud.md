# Session: cloud

Experimental, not for real work, until the live test (#942) passes. Each worker is a Claude Code cloud session on claude.ai, started from a local session; the cloud session sees only itself, so its manager starts, lists and closes it. No plugin loads there, so the worker reads `teamwork/skills/kick-off/SKILL.md` by path from its checkout, and gets the teamwork hooks from the repository's `.claude/settings.json`, which runs them only where `CLAUDE_CODE_REMOTE` is `true`; a repository without that file gives its cloud worker no hook.

| operation | how |
| --- | --- |
| `start` | from the checkout on the pushed base branch, `claude --permission-mode auto --cloud "<prompt>"`, `--permission-mode` first, since `--cloud` takes the next word as its prompt; the prompt: `You are <name>. Read teamwork/skills/kick-off/SKILL.md and follow it as invoked with: <kick-off arguments>`. It runs in the environment last made on claude.ai, and the tier and effort are not passed |
| `close` | the worker, after its close summary, calls `archive_session` on its own session id; when that is refused, its manager asks the owner to archive it on claude.ai/code |
| `rename` | `set_session_title` on its own session, then `echo <name> > ~/.teamwork-name`, which the hooks read as its name |
| `list` | `ListAgents` from an interactive local session, its rows marked `cloud`, each named by its title; not available from a headless `claude -p` session |
| `screen` | not available: `claude --teleport <session id>` in a trusted checkout shows its last message and leaves it in the cloud |
| `answer` | not available: a `ListAgents` row `waiting on a human` is a tool prompt the owner answers on claude.ai/code, so `notify` the owner |
| `reload` | not available: no plugin loads, and the worker reads each playbook again by path |

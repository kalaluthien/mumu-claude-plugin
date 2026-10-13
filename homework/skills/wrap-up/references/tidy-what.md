# Tidy targets

What a tidy reads, found afresh in the project at hand: list what exists with
`git ls-files` and a glob, never assume a layout.

| target | where it lives | drift to look for |
| --- | --- | --- |
| Claude memory: instruction files | `AGENTS.md` and `CLAUDE.md` from the project root down, `.claude/rules/`, and `<config>/CLAUDE.md` | a rule stated twice, rules that contradict, a line that restates what the repository shows, a path or command that no longer exists |
| Claude memory: auto-memory | this project's pool, `<config>/projects/<key>/memory/`, and any pool holding a copy of one of its lessons | what `<skill>/scripts/list-drift.py` prints; one lesson in several files or pools; an entry a later one replaces; a lesson an instruction file or skill should hold |
| project documents | `README.md` and the other documents the repository keeps for people, such as `docs/` and `CONTRIBUTING.md` | a step, file or command the repository no longer has; two documents that disagree |
| project skills | `.claude/skills/*/SKILL.md` and the skills of plugins the repository owns, with their references and scripts | a description that overlaps another skill's, a skill grown past a few focused parts, a recipe (`.claude/skills/run-*/`) whose commands fail |

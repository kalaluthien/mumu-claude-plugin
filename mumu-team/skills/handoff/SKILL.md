---
name: handoff
description: Use when a request in plain words asks for work in a project's repository and this session is not a mumu-team lead or worker - it files the request as a root goal there and hands it to that project's lead, starting one if none is live. Not for a lead or worker session, which routes work by its own rules.
argument-hint: 로그인 타임아웃 고쳐 줘, kalaluthien/garden
---

# Handoff

Hand the owner's request to the project's lead: the one session that holds its goals. The words of [kickoff's Domain](${CLAUDE_PLUGIN_ROOT}/skills/kickoff/SKILL.md) and its [repo.md](${CLAUDE_PLUGIN_ROOT}/skills/kickoff/references/repo.md) verbs apply.

1. The project is the repository the words name, else the cwd's. Its checkout is the parent of `git rev-parse --path-format=absolute --git-common-dir` run in the cwd, or its line `<folder> <owner/repo>` in `~/workspace/repos.txt`: `~/workspace/<folder>/<repo>`, or `~/workspace/<folder>` when the folder ends in `/`. A project in neither is the owner's to add there or drop: ask with `AskUserQuestion`.
2. `file` a root goal in that repository: a title of the request, `## Goal` quoting the owner's words as said, and `## Definition of done` as `- set by <repo>-lead`, since the lead asks the owner for its criteria.
3. `herdr agent list` shows `<repo>-lead`: `herdr agent prompt <repo>-lead "see <goal-url>"`. Otherwise `lead-start.py <checkout> <goal-url>`, which starts it as `--agent mumu-team:lead` and prompts it; a start-up dialog in its new tab is the owner's to answer there.
4. Tell the owner which lead holds the goal, its url, and that the work goes on in that lead's tab.

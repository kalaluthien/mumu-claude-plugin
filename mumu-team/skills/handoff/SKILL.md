---
name: handoff
description: Use when a request in plain words asks for work in a project's repository and this session is not a mumu-team lead or worker - it files the request as a root task there, or adds follow-up words to one already open, and hands it to that project's lead, starting one if none is live. Not for a lead or worker session, which routes work by its own rules.
argument-hint: 로그인 타임아웃 고쳐 줘, kalaluthien/garden
---

# Handoff

Hand the owner's request to the project's lead: the one session that holds its tasks. The words of [kickoff's Domain](${CLAUDE_PLUGIN_ROOT}/skills/kickoff/SKILL.md) and Verbs apply.

1. The project is the repository the words name, else the cwd's. Its checkout is the parent of `git rev-parse --path-format=absolute --git-common-dir` run in the cwd, or its line `<folder> <owner/repo>` in `~/workspace/repos.txt`: `~/workspace/<folder>/<repo>`, or without `<repo>` when the folder ends in `/`. A project in neither is the owner's to add there or drop: ask with `AskUserQuestion`.
2. Words that add to a task already open there (`gh issue list -R <repo> --search "<words> -label:backlog"`): `comment` them on it, as said, and go to step 3 with its url. Otherwise `file` a root task in that repository, labelled `effort:medium`: a title of the request, `## Goal` quoting the owner's words as said, and `## Definition of done` as `- set by <repo>-lead`, since the lead asks the owner for its criteria.
3. The lead is `<repo>-lead`, or, in a repository with `scope:` labels (`gh label list -R <repo> --search scope:`), `<folder>-lead`: the folder of the plugin the words name, else the folder the work touches, else the owner's to pick with `AskUserQuestion`; label the task `scope:<folder>` with `gh issue edit <task-url> --add-label scope:<folder>`.
4. `live` shows that lead: `prompt` it `see <task-url>`. Otherwise `lead-start.py <checkout> <task-url>`, which starts it as `--agent mumu-team:lead` and prompts it, and a folder lead names itself from the task's label; a start-up dialog in its new tab is the owner's to answer there.
5. Tell the owner which lead holds the task, its url, and that the work goes on in that lead's tab.

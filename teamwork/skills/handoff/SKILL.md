---
name: handoff
description: Use when a request in plain words asks for work in a project's repository and this session is not a teamwork lead or worker, or when the owner asks this session to become the project's lead ("너 lead로 승격해"). Never for a lead or worker session.
argument-hint: 로그인 타임아웃 고쳐 줘, kalaluthien/garden
---

# Handoff

Hand the owner's words to the project's lead, in the terms and verbs of [kickoff's Domain](${CLAUDE_PLUGIN_ROOT}/skills/kickoff/SKILL.md).

1. The project is the repository the words name, else the cwd's. Its checkout is the parent of `git rev-parse --path-format=absolute --git-common-dir` run in the cwd, or its line `<folder> <owner/repo>` in `~/workspace/repos.txt`: `~/workspace/<folder>/<repo>`, or without `<repo>` when the folder ends in `/`. For a project in neither, ask the owner with `AskUserQuestion` to add it there or drop it.
2. The lead is `<repo>-lead`, or, in a repository with `scope:` labels (`gh label list -R <repo> --search scope:`), `<folder>-lead`: the folder of the plugin the words name, else the folder the work touches, else the owner's to pick with `AskUserQuestion`.
3. Words that ask for an issue or name one:
   - Words that name a task already open there, by number, url or title (`gh issue list -R <repo> --search "<words> -label:backlog"`): `comment` them on it, as said.
   - Otherwise `file` a root task in that repository, labelled `scope:<folder>` with a folder: a title of the request, `## Goal` quoting the owner's words as said, and `## Definition of done` as `- set by <lead>`.
   - `live` shows the lead: `prompt` it `see <task-url>`. Otherwise `start-lead` it with the task's url.
4. Words asking this session itself to become the lead ("너 lead로 승격해"), with none live: run `lead-start.py <checkout> --replace`, adding `--folder <folder>` for a folder lead, as one Bash call of its own. Then `prompt` the lead this session's context as words: what the owner asked, what was done and what is left, with urls and paths; go to 6 and end the turn. A live lead: `prompt` it those words instead, and this session stays.
5. Any other plain words file no issue: `start-lead` the lead unless `live` shows it; then `prompt` it the words as said.
6. Tell the owner which lead has the words, the task's url if any, and that the work goes on in that lead's tab.

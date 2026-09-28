---
name: handoff
description: Use when a request in plain words asks for work in a project's repository and this session is not a mumu-teamwork lead or worker - it reaches that project's lead, or its plugin folder's, starting one if none is live, and hands it the words, filing them as a root task only when they ask for an issue or name one; also when the owner asks this session to become the project's lead ("너 lead로 승격해"), replacing it. Not for a lead or worker session, which routes work by its own rules.
argument-hint: 로그인 타임아웃 고쳐 줘, kalaluthien/garden
---

# Handoff

Hand the owner's words to the project's lead: the one session that holds its tasks. The words of [kickoff's Domain](${CLAUDE_PLUGIN_ROOT}/skills/kickoff/SKILL.md) and Verbs apply.

1. The project is the repository the words name, else the cwd's. Its checkout is the parent of `git rev-parse --path-format=absolute --git-common-dir` run in the cwd, or its line `<folder> <owner/repo>` in `~/workspace/repos.txt`: `~/workspace/<folder>/<repo>`, or without `<repo>` when the folder ends in `/`. A project in neither is the owner's to add there or drop: ask with `AskUserQuestion`.
2. The lead is `<repo>-lead`, or, in a repository with `scope:` labels (`gh label list -R <repo> --search scope:`), `<folder>-lead`: the folder of the plugin the words name, else the folder the work touches, else the owner's to pick with `AskUserQuestion`.
3. Issue-shaped words, which ask for an issue or name one, go through an issue and kickoff:
   - Words that name a task already open there, by number, url or title (`gh issue list -R <repo> --search "<words> -label:backlog"`): `comment` them on it, as said.
   - Otherwise `file` a root task in that repository, labelled `effort:medium` and, with a folder, `scope:<folder>`: a title of the request, `## Goal` quoting the owner's words as said, and `## Definition of done` as `- set by <lead>`, since the lead asks the owner for its criteria.
   - `live` shows the lead: `prompt` it `see <task-url>`. Otherwise `lead-start.py <checkout> <task-url>`, adding `--folder <folder>` for a folder lead.
4. Words asking this session itself to become the lead ("너 lead로 승격해"), with none live: run `lead-start.py <checkout> --replace`, adding `--folder <folder>` for a folder lead, as one Bash call of its own; it starts the lead and, once this turn ends, closes this session and its tab. Then `prompt` the lead this session's context as words: what the owner asked, what was done and what is left, with urls and paths; tell the owner the work goes on in the lead's tab, and end the turn. A live lead: `prompt` it those words instead, and this session stays.
5. Any other plain words file no issue: `live` shows the lead, else start it with `lead-start.py <checkout>`, adding `--folder <folder>` for a folder lead; then `prompt` it the words as said.
6. `lead-start.py` starts the lead as `--agent mumu-teamwork:lead` in its own tab and prompts its kickoff; a start-up dialog there is the owner's to answer. Tell the owner which lead has the words, the task's url if any, and that the work goes on in that lead's tab.

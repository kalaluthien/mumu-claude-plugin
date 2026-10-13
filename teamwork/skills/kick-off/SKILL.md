---
name: kick-off
description: Use when a session is made its project's manager, by the owner or by another session, or is started as a worker by its manager. Not for the judge or another subagent, whose brief names the files it reads.
disable-model-invocation: true
argument-hint: 로그인 타임아웃 고쳐 줘
---

# Kick-off

Bring the owner's work to pull requests merged at a head the judge approved, through one manager and its workers.

Arguments: $ARGUMENTS

## Route

Match the arguments to the first row that fits, open its playbook with `Read`, and copy its steps verbatim into the todo list; a step not done stays, marked skipped with its reason.

| arguments | role | playbook |
| --- | --- | --- |
| `work <task-url> manager <name>` | worker | [references/worker.md](references/worker.md) |
| `succeed <name>` | manager | [references/manager.md](references/manager.md)'s Succession |
| anything else: `see <url>`, the owner's words, or none | manager | [references/manager.md](references/manager.md) |

**Role by name**: once started, a session's name says its role: a manager's ends in `-manager`, a worker's is `<topic>-<n>-<k>`.

## Vocabulary

| term | meaning |
| --- | --- |
| team | one manager and its workers, alone in one terminal workspace |
| manager | the one session per project, or per plugin folder in a repository with `scope:` labels, that files tasks, starts workers and answers them |
| worker | a session on one task, in its own worktree on its own branch |
| judge | a fresh subagent, the only one that approves, given only its playbook's path and the url to judge, as `judge` says |
| task | one change, ending in one pull request, or in a report comment when its definition of done names one; its body is `## Goal` and `## Definition of done`, edited in place |
| backlog | the owner's words kept for later, as said, filed labelled `backlog` and never worked until the manager rewrites them as a task |
| criterion | one line of a definition of done: `[check]`, a command whose output decides the pass, quoted failing on main; or `[score]`, the judge's score by its rubric, one comparing head with main naming its sample and margin; a check that can fail, and that the honest empty outcome can pass |
| record | a comment opening with a keyword of Records |
| name | one string for a session, its tab, its first pane and its agent, and a worker's worktree and branch: `<topic>-<n>-<k>` for task n, attempt k, the topic 2-4 lowercase words joined by `-`; `<repo>-manager`, or `<folder>-manager` in a repository with `scope:` labels, `<repo>` lowercased, each run of other characters one `-`, cut to 22 before the suffix; an agent or the owner may add panes to a tab for work |

## Records

| keyword | written by | form |
| --- | --- | --- |
| `BLOCKED:` | worker | `BLOCKED: <question>`, or `BLOCKED: stuck on <criterion>` |
| `DECIDED:` | manager | `DECIDED: <answer>` |
| `APPROVED:` | judge | `APPROVED: <sha>`, a pull request at that head; `APPROVED: <comment-url>`, a report; `APPROVED:` alone, a plan |
| `FINDINGS:` | judge | one line per gap, as `judge.md` says |

Write a keyword in capitals; read it in any case.

## Rules

- **See a url**: a session prompts another only `see <url>`, the url holding what it means; on `see <url>`, `read` it and act only on what it shows still open.
- **Judge approves**: work lands only as a pull request merged at a head the judge approved, or a report it approved; no script enforces this, so check the `APPROVED:` sha against the head yourself before `merge`.
- **Verdicts are the judge's**: never post `APPROVED:` or `FINDINGS:` yourself; after fixing a `FINDINGS:`, resume that judge with `see <url>`; when its comment is refused, resume it once the owner allows.
- **Side branch**: commit and push only on a branch other than the default; fix what a git hook refuses, never skip it.
- **File first**: write a body, a comment or a decision to a scratch file with a file tool, then post it with `--body-file`.
- **Short writing**: bullets or a table, no narration; cite urls, `path:line`s and shas; a title verb-first, at most 40 characters.
- **Criteria table**: a pull request body is `Closes #<task>`, or no task for a small change, over a table of each criterion, the command run, its result with the line that shows it, and an `on main` column with its failing output on the default branch; a report comment is its findings over the same table.

## Verbs

Tasks and pull requests live on GitHub, a task being an issue. The default branch is `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`.

| verb | command |
| --- | --- |
| `read` | `gh issue view <url> --json title,body,comments,labels,state`, or `gh pr view <url> --json title,body,comments,headRefOid,state` |
| `file` | `gh label create <label> --force` per label, then `gh issue create -R <repo> --title "<title>" --label <label>... --body-file <path>` |
| `order` | make a task wait on another: `gh api -X POST repos/<repo>/issues/<n>/dependencies/blocked_by -F issue_id=<id>`, `<id>` from `gh api repos/<owner>/<repo>/issues/<m> -q .id` |
| `comment` | `gh issue comment <url> --body-file <path>`; `decide` is a `comment` of a `DECIDED:` |
| `pr` | `gh pr create --base <default> --head <branch> --title "<title>" --body-file <path>`; later `gh pr edit <pr> --body-file <path>` |
| `merge` | `gh pr merge <pr-url> --squash --delete-branch` |
| `resolve` | `gh issue close <url> --reason completed --comment "<summary>"` |
| `judge` | `Agent` on model `opus`, its prompt `Read ${CLAUDE_PLUGIN_ROOT}/skills/kick-off/references/judge.md, then judge <url>.` and nothing more; resume it with `SendMessage` |
| `stop` | `gh issue close <url> --reason "not planned" --comment "<reason>"`, then `gh pr close <pr-url>` |

A session lives in a terminal multiplexer; with herdr, address every command to a name:

| verb | command |
| --- | --- |
| `live` | `herdr agent list`: each agent's `name`, `pane_id`, `tab_id`, `workspace_id` and `agent_status` |
| `rename` | name yourself `<name>`: `herdr tab rename <tab> <name>` and `herdr pane rename $HERDR_PANE_ID <name>`, the tab from `herdr pane get $HERDR_PANE_ID`, then `herdr agent rename $HERDR_PANE_ID <name>` and `herdr agent prompt $HERDR_PANE_ID "/rename <name>"`; a manager also `herdr workspace rename <workspace> <name>` |
| `start` | `${CLAUDE_PLUGIN_ROOT}/skills/kick-off/scripts/start-session.py <name> <cwd> "<prompt>" [--team] [--model <m> --effort <e>] [-- <claude flags>]`: a new tab in your team, or with `--team` a new team's workspace |
| `look` | `herdr agent read <name> --lines 40`: the session's screen |
| `prompt` | `herdr agent prompt <name> "<text>"`; `look` after, and resend once when no turn carries the text |
| `close` | `${CLAUDE_PLUGIN_ROOT}/skills/kick-off/scripts/close-session.py <name>`, your own name included |

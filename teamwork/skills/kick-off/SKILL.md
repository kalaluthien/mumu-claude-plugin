---
name: kick-off
description: Use when a session is made its project's manager, by the owner or by another session, or is started as a worker by its manager. Not for the judge or another subagent, whose brief names the files it reads.
disable-model-invocation: true
argument-hint: 로그인 타임아웃 고쳐 줘
---

# Kick-off

Turn the owner's intent into merged work: one manager per project routes it, workers define and do it.

Arguments: $ARGUMENTS

## Route

Open the playbook of the first row that fits with `Read` and follow it; the `route-event` hook names it again at each session start.

| arguments | role | playbook |
| --- | --- | --- |
| `worker <name> manager <manager>`, then a url or the owner's words | worker | [references/worker.md](references/worker.md) |
| `succeed <name>` | manager | [references/manager.md](references/manager.md)'s Succession |
| anything else | manager | [references/manager.md](references/manager.md) |

## Vocabulary

| term | meaning |
| --- | --- |
| project | a repository, or its folder named by a `scope:` label; its name lowercased, each run of other characters one `-`, cut to 22 |
| manager | `<project>-manager`, the one session per project, alone with its workers in one terminal workspace |
| worker | `<task>-worker`, `<task>` 2-4 words of its work, in a worktree and branch of its name; it may rename itself |
| holds | a worker holds each open issue that names it; it may hold none, one or several, and several may hold one |
| backlog | an issue labelled `backlog`: the owner's intent in rough words, written by the manager |
| task | an issue a worker defines: `## Goal`, `## Definition of done` of criteria, and its order after other tasks |
| criterion | a `[check]`, a command whose output decides, quoted failing on main; or a `[score]` by a rubric over a named sample, head against main |
| record | a comment opening `BLOCKED:`, a worker's question, or `DECIDED:`, the manager's answer, route or order |
| judge | a fresh subagent that reviews work it did not write and replies to its caller alone |

## Rules

- **Talk**: reach a session by `SendMessage` to its name from `ListAgents`, one message naming the url that holds what it needs, so any request, answer or handback reads the same; prompt only `/teamwork:kick-off` through `start` and your own `/rename`. Whatever must outlive a session goes on its issue first.
- **Side branch**: commit and push only on a branch other than the default; fix what a git hook refuses, never skip it.
- **Short writing**: bullets or a table, no narration; cite urls, `path:line`s and shas; a title verb-first.

## Verbs

Issues and pull requests live on GitHub, sessions in herdr, addressed by name; the default branch is `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`.

| verb | command |
| --- | --- |
| `read` | `gh issue view <url> --json title,body,comments,labels,state`, or `gh pr view <url> --json title,body,comments,headRefOid,state` |
| `file` | `gh label create <label> --force` per label, then `gh issue create -R <repo> --title "<title>" --label <label>... --body-file <path>` |
| `order` | `gh api -X POST repos/<repo>/issues/<n>/dependencies/blocked_by -F issue_id=<id>`, `<id>` from `gh api repos/<repo>/issues/<m> -q .id` |
| `comment` | `gh issue comment <url> --body-file <path>`; `decide` is a `comment` of a `DECIDED:` |
| `resolve` | `gh issue close <url> --reason completed --comment "<summary>"`, or `--reason "not planned"` for work stopped |
| `judge` | `Agent` on `sonnet` at `high`, its prompt `Read ${CLAUDE_PLUGIN_ROOT}/skills/kick-off/references/judge.md, then judge <url or path>.`; resume it with `SendMessage` |
| `rename` | `herdr tab rename <tab> <name>` and `herdr pane rename $HERDR_PANE_ID <name>`, the tab from `herdr pane get $HERDR_PANE_ID`, then `herdr agent rename $HERDR_PANE_ID <name>` and `herdr agent prompt $HERDR_PANE_ID "/rename <name>"`; a manager also `herdr workspace rename <workspace> <name>` |
| `start` | `${CLAUDE_PLUGIN_ROOT}/skills/kick-off/scripts/start-session.py <name> <cwd> "<kick-off arguments>" --model <m> --effort <e> [--team]`: a tab in your workspace, or with `--team` a new one |
| `look` | `herdr agent read <name> --lines 40`: the session's screen |
| `close` | `${CLAUDE_PLUGIN_ROOT}/skills/kick-off/scripts/close-session.py <name>`, your own name included |

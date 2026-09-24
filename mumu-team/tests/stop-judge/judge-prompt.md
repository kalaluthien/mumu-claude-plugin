Condition to verify: this worker session may end its turn now. `ok` true means it may stop; `ok` false means it must keep working. Hook input: $ARGUMENTS

The worker owns one GitHub issue. Its number `n` is the trailing number of the worktree directory in `cwd` (`.claude/worktrees/<topic>-<n>`), and its branch is that directory's name. Run exactly these two commands with Bash, each alone as written with `<n>` and `<branch>` filled in: no `cd`, no pipe, no other command, since the shell already runs in `cwd` and nothing else is allowed.

    gh issue view <n> --json state,comments
    gh pr list --head <branch> --state all --json number,state,comments

Trust only what they print: the worker's last message is a claim, not evidence. All comments come from one account, so tell the worker from the leader by what a comment says.

The worker may stop (`ok` true) when any of these holds:

1. The issue is closed, or its pull request is merged.
2. A comment starting `BLOCKED:` (a question, or `BLOCKED: stuck on ...`) is unanswered: no later comment answers it. `Answer:`, `Criteria changed:` or any reply to the question after it is an answer, and then the worker goes on; the worker's own later note adding detail to the question is not. A question without the `BLOCKED:` prefix never counts.
3. The leader posted `Stopped: <reason>`.
4. The worker waits on another worker's issue, recorded on its own issue: a consensus proposal to that worker, or a note naming the other issue it waits on, with no later reply.
5. A comment says the issue is held by another session.

Example: comments `BLOCKED: which port?` then `Answer: 8080.` → `ok` false: the question is answered, so the worker applies the answer, even if its last message says it will stop.

Otherwise it must keep working (`ok` false), with `reason` naming its next step: merge an approved pull request, fix findings, launch the reviewer, open the pull request, or comment `BLOCKED: <question>` for a question not posted that way.

Answer with the JSON only: `{"ok": true}` when the worker may stop, even when it is waiting; `{"ok": false, "reason": "<next step>"}` when it must keep working.

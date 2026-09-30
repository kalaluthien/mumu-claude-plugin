# Work

Rules for every step:

- Before building, read the prior work in the repository and its issues; for a new mechanism or API, also the official docs and a web example.
- For a decision that is not yours, for work that needs its own pull request or waits on another task, and for a criterion you think wrong, cannot check or that the honest empty outcome cannot pass: `comment` `BLOCKED: <question>` on the task, `prompt` the lead `see <task-url>`, and stop until it prompts you back with a `DECIDED:`.
- End each flow by `prompt`ing the lead `see <url>` of what it produced.
- Send the owner a `PushNotification`, loaded through `ToolSearch`, only in these cases, each naming the task, the reason and your tab:
  - A step auto mode refuses: name the step, and wait for the owner in your tab, posting no `BLOCKED:`. A refused self-modifying edit, to a rules, guard or agent file, goes as a patch instead: write the change with the Write tool as a patch in your scratchpad, check it with `git apply --check <patch-path>`, and have the `PushNotification` name exactly one owner command, `! git -C <worktree> apply <patch-path>`, both paths absolute; then wait in bounded foreground Bash polls until `git apply --reverse --check <patch-path>` passes, and commit, push and finish to merge with no further owner turn.
  - An `APPROVED:` pull request waiting on the owner's sign-off: name its url, after the `BLOCKED: owner sign-off on <pr-url>` of step 4.
  - Your lead unreachable, `prompt` having failed twice: name the url you were sending it.
- On a split task, your share is the one your topic names and your criteria only its DoD ids; write only your pull request and `BLOCKED: <share>: ...` comments.
- While your own judge or eval runs, wait in one bounded foreground Bash poll instead of stopping.
- Narrowing a scope is not yours: a gate you think a change does not need goes as `BLOCKED:` on your task asking for a `gates.json` change as its own task, and meanwhile you run it.
- A finding is closed by fixing the cause of the gap it names, never by rewording, loosening a test or editing a criterion.
- At a `FINDINGS:`, fix, rerun the reproduction each finding quotes and every criterion, and post what was judged again: push, `comment` the report, or post the backlog's body.

Steps, resumed at the one the task and its pull request or report show:

1. Work in the task's worktree, the one `git worktree list` names `<topic>-<n>-<k>`. `read` the task. A task whose `## Definition of done` names a report comment goes by Report below.
2. `claim` the attempt; held by another session: `BLOCKED: held by <branch>`.
3. Implement, commit, push, and write the criteria table into the `pr` body, opening the `pr` at the first push; then run each criterion whose files changed since it last passed, and each gate but the judge that `scope` prints and `merge` names, and `comment` one `PASSED:` on the pull request naming those that passed; repeat per iteration. After 3 iterations without a criterion newly passing, post `BLOCKED: stuck on <criterion>`.
4. With every criterion passing, launch the `judge` on the pull request's url when `scope` prints it, and name its model in the body. `merge`; refused as behind or by GitHub, merge the default branch in, rerun only the gates `pr-merge.py` names, push, and run `merge` again, and only when `pr-merge.py` names the judge, resume it. `APPROVED:` while the owner's sign-off is pending: push the pending commit, else post `BLOCKED: owner sign-off on <pr-url>`.

## Siblings

- Find your siblings in `ListAgents` as `<share>-<n>-*`; read a merged share from its pull request.
- Before you change a file, an interface or a rule that a sibling's share or its open pull request (`gh pr diff <pr> --name-only`) also touches, send that sibling's worker a proposal, and put its outcome in your pull request body.

## Report

1. Do the work the task asks, then rerun every criterion and `comment` the report on the task.
2. Launch the `judge` on that comment's url. `APPROVED:` naming your newest report: `resolve` the task.

## Survey

Make no claim, branch or pull request, and leave the backlog open and labelled `backlog`:

1. `read` the backlog and its comments, then research what the owner's words ask: the repository, its issues (`gh search issues "<words>" -R <repo> --include-prs`) and the official docs.
2. Write the body to `<path>` as the owner's words exactly as `read` shows them, then one `## Survey` section of findings, each claim citing a url or `path:line`, replacing any survey already there. Post it with `gh issue edit <backlog-url> --body-file <path>`.
3. Launch the `judge` on the backlog's url.

## Subagents

Launch one only for an independent track of more than a few reads or edits.

- Give two subagents at once different files, scratch files included.
- Brief one with the ask verbatim under its own label, adding no premise of your own, and set its bounds as the harness enforces them.
- Check once each claim of its report that names no command, `path:line` or url, each brief section it leaves unmentioned, and each "not found".

# Work

Rules for every step:

- Before building, read the prior work in the repository and its issues, and the official docs and a web example only for a new mechanism or API.
- Work that needs its own pull request, or waits on another task, is the leader's to `file`, `order` and `start`: ask for it as a decision that is not yours.
- A decision that is not yours: `comment` `BLOCKED: <question>` on the task, `prompt` the leader `see <task-url>`, and stop until it prompts you back with a `DECIDED:`.
- Owner notices: send the owner a `PushNotification`, loaded through `ToolSearch`, only in these cases, each naming the task, the reason and your tab, since the owner may be away from the terminal; none for progress, a merge, or a `BLOCKED:` your leader answers, which it relays:
  - A step auto mode refuses: name the step, and wait for the owner in your tab, posting no `BLOCKED:`, since only the owner can allow it. A refused self-modifying edit, to a rules, guard or agent file, goes as a patch instead: write the change with the Write tool as a patch in your scratchpad, check it with `git apply --check <patch-path>`, and have the `PushNotification` name exactly one owner command, `! git -C <worktree> apply <patch-path>`, both paths absolute; then wait in bounded foreground Bash polls until `git apply --reverse --check <patch-path>` passes, and commit, push and finish to merge with no further owner turn.
  - An `APPROVED:` pull request waiting on the owner's sign-off: name its url, after the `BLOCKED: owner review of <pr-url>` of step 4.
  - Your leader unreachable, `prompt` having failed twice: name the url you were sending it.
- A task whose body has `## Shares` (share | DoD | after | with) is split: your share is the row your topic names and your criteria only its DoD ids; without it, the task is one share, whole.
- The task's body, labels and close are the leader's; as a share's worker you write only your pull request and `BLOCKED: <share>: ...` comments.
- A share's pull request says `Part of #n`, never a closing keyword, and the leader resolves the task once every row has merged.
- While your own judge or eval runs, wait in one bounded foreground Bash poll instead of stopping.
- A finding is closed by fixing the cause of the gap it names, never by rewording, loosening a test or editing a criterion; a criterion you think wrong is a decision that is not yours: `BLOCKED:`.

Steps, resumed at the one the task and its pull request or report show:

1. Work in the task's worktree, the one `git worktree list` names `<topic>-<n>-<k>`. `read` the task. A task whose `## Definition of done` names a report comment goes by Report below, with no `claim` or pull request. Otherwise `claim` the attempt; held by another session, `comment` `BLOCKED: held by <branch>` on the task, `prompt` the leader `see <task-url>`, and stop.
2. Review each criterion of the task: one you cannot check, or that the honest empty outcome cannot pass, is a decision that is not yours.
3. Implement, then rerun every criterion, commit, push, and write the criteria table into the `pr` body, opening the `pr` at the first push; repeat per iteration. After 3 iterations without a criterion newly passing, `comment` `BLOCKED: stuck on <criterion>` and go on as for any decision that is not yours.
4. With every criterion passing, launch the `judge` on the pull request's url with the model `review-model.py origin/<default> HEAD` prints, and name it in the body. `FINDINGS:`: fix, rerun the reproduction each finding quotes and every criterion at the new head, push, and resume that judge with `see <pr-url>`, launching a new one when it cannot be resumed and the pull request shows no verdict at the head yet. `APPROVED: <head>`, or an older sha `merge.py` carries to the head: `merge` as a Bash call of its own, since an allow rule matches a compound command only when every part does; refused as behind or by GitHub, merge the default branch in, rerun every check on the merged tree only when `merge.py` names a path both sides change, push, and run `merge` again, and only when `merge.py` refuses it, resume the judge the same way. `APPROVED:` while the owner's sign-off is pending: push the pending commit, else `comment` `BLOCKED: owner review of <pr-url>`. Merged, which closes the task unless it is split: `prompt` the leader `see <pr-url>`.

## Siblings

A share's worker agrees a change that crosses its split with a sibling's worker, as leads agree across folders:

- Your siblings are the live workers of your task's other rows, the sessions `ListAgents` names `<row>-<n>-*`, and your row's `with` names what you share with which; a merged row is read from its pull request, not messaged.
- Before you change a file, an interface or a rule that a sibling's row or its open pull request (`gh pr diff <pr> --name-only`) also touches, send that sibling's worker a proposal through `SendMessage`, opening `Proposal from <name>:` and ending `Reply OK or an objection.`, and act after its answer.
- The answer is `OK`, or an objection with its reason.
- An objection: revise the proposal and ask again.
- Past two objections, or no answer after one resend: `comment` `BLOCKED: <share>: <question>` and go on as for any decision that is not yours.
- Record only the outcome, in your pull request body, never the exchange.

## Report

1. Do the work the task asks, then rerun every criterion and `comment` the report on the task as one comment: the findings, then the criteria table.
2. Launch the `judge` on that comment's url on Opus. `FINDINGS:`: fix, rerun every criterion, `comment` the report again, and resume that judge with `see <comment-url>`. `APPROVED: <comment-url>` naming your newest report: `resolve` the task, then `prompt` the leader `see <task-url>`.

## Survey

A backlog's survey worker, prompted `survey <backlog-url> leader <address>`, has no claim, branch or pull request, and leaves the issue open and labelled `backlog`:

1. `read` the backlog and its comments, then research what the owner's words ask: the repository, its issues (`gh search issues "<words>" -R <repo> --include-prs`) and the official docs.
2. Write the body to `<path>` as the owner's words exactly as `read` shows them, then one `## Survey` section of findings, each claim citing a url or `path:line`; a survey already there is rewritten, so the body keeps exactly one. Post it with `gh issue edit <backlog-url> --body-file <path>`.
3. Launch the `judge` on the backlog's url on Opus. `FINDINGS:`: fix, post the body again, and resume that judge with `see <backlog-url>`. `APPROVED:`: `prompt` the leader `see <backlog-url>`.

## Subagents

Launch one for any independent track you judge worth it, such as a wide multi-file search or a rival approach; a job of a few reads or edits is quicker done yourself.

- Give two subagents at once different files, scratch files included: they share your branch and scratchpad.
- Brief one with the ask verbatim under its own label, adding no premise of your own, and set its bounds as the harness enforces them (a sha to read, a worktree, its tools), since a prose "do not" binds nothing, nor reaches what it launches unless the brief says so.
- Its final message is its report: one naming no command, `path:line` or url, a brief section it leaves unmentioned, and a "not found", are unchecked until one check of yours.

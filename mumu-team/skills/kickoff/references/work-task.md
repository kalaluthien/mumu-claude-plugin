# Work

Rules for every step:

- Before building, read the prior work in the repository and its issues, and the official docs and a web example only for a new mechanism or API.
- Work that needs its own pull request, or waits on another task, is the leader's to `file`, `order` and `start`: ask for it as a decision that is not yours.
- A decision that is not yours: `comment` `BLOCKED: <question>` on the task, `prompt` the leader `see <task-url>`, and stop until it prompts you back with a `DECIDED:`.
- A task whose body has `## Shares` (share | DoD | after) is split: your share is the row your topic names and your criteria only its DoD ids; without it, the task is one share, whole.
- The task's body, labels and close are the leader's; as a share's worker you write only your pull request and `BLOCKED: <share>: ...` comments.
- A share's pull request says `Part of #n`, never a closing keyword, and the leader resolves the task once every row has merged.
- While your own reviewer or eval runs, wait in one bounded foreground Bash poll instead of stopping.

Steps, resumed at the one the task and its pull request or report show:

1. Work in the task's worktree, the one `git worktree list` names `<topic>-<n>-<k>`. `read` the task. A task whose `## Definition of done` names a report comment goes by Report below, with no `claim`, branch or pull request. Otherwise `claim` the attempt; held by another session, `comment` `BLOCKED: held by <branch>` on the task, `prompt` the leader `see <task-url>`, and stop.
2. Review each criterion of the task: one you cannot check, or that the honest empty outcome cannot pass, is a decision that is not yours.
3. Implement, then rerun every criterion, commit, push, and write the criteria table into the `pr` body, opening the `pr` at the first push; repeat per iteration. After 3 iterations without a criterion newly passing, `comment` `BLOCKED: stuck on <criterion>` and go on as for any decision that is not yours.
4. With every criterion passing, launch the `reviewer` on the pull request's url with the model `review-model.py origin/<default> HEAD` prints, and name it in the body. `FINDINGS:`: fix, rerun the reproduction each finding quotes and every criterion at the new head, push, and resume that reviewer with `see <pr-url>`, launching a new one when it cannot be resumed and the pull request shows no verdict at the head yet. `APPROVED: <head>`: `merge` as a Bash call of its own, since an allow rule matches a compound command only when every part does; refused as behind or by GitHub, merge the default branch in, rerun every check on the merged tree, push, and resume the reviewer the same way. `APPROVED:` while the owner's sign-off is pending: push the pending commit, else `comment` `BLOCKED: owner review of <pr-url>`. Merged, which closes the task unless it is split: `prompt` the leader `see <pr-url>`.

## Report

1. Do the work the task asks, then rerun every criterion and `comment` the report on the task as one comment: the findings, then the criteria table.
2. Launch the `reviewer` on that comment's url on Opus. `FINDINGS:`: fix, rerun every criterion, `comment` the report again, and resume that reviewer with `see <comment-url>`. `APPROVED: <comment-url>` naming your newest report: `resolve` the task, then `prompt` the leader `see <task-url>`.

## Subagents

Launch one only for a large, independent track, such as a wide multi-file search; a job of a few reads or edits is yours.

- Give two subagents at once different files, scratch files included: they share your branch and scratchpad.
- Brief one with the ask verbatim under its own label, adding no premise of your own, and set its bounds as the harness enforces them (a sha to read, a worktree, its tools), since a prose "do not" binds nothing, nor reaches what it launches unless the brief says so.
- Its final message is its report: one naming no command, `path:line` or url, a brief section it leaves unmentioned, and a "not found", are unchecked until one check of yours.

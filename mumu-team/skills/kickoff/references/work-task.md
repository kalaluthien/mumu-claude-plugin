# Work

Work one task of a goal, as the worker its leader started.

Rules for every step:

- Before building, read the prior work in the repository and its issues, and the official docs and a web example only for a new mechanism or API.
- Work that needs its own pull request, or waits on another task, is the leader's to `file`, `order` and `start`: ask for it as a decision that is not yours.
- A decision that is not yours: `comment` `BLOCKED: <question>` on the task, `prompt` the leader `see <task-url>`, and stop until it prompts you back with a `DECIDED:`.

Steps:

1. Work in the task's worktree, the one `git worktree list` names `*-<n>-<k>`. `read` the task and its parent goal, if any. A task whose `## Definition of done` names a report comment goes by Report below, with no `claim`, branch or pull request. Otherwise `claim` the attempt; held by another session, `comment` `BLOCKED: held by <branch>` on the task, `prompt` the leader `see <task-url>`, and stop.
2. Review each criterion of the task: one you cannot check, or that the honest empty outcome cannot pass, is a decision that is not yours.
3. Implement, then rerun every criterion, commit, push, and write the criteria table into the `pr` body, opening the `pr` at the first push; repeat per iteration. After 3 iterations without a criterion newly passing, `comment` `BLOCKED: stuck on <criterion>` and go on as for any decision that is not yours.
4. With every criterion passing, launch the `reviewer` on the pull request's url with `model` set to what `review-size.py origin/<default> HEAD` prints, `sonnet` for at most 20 changed lines and `opus` above, and name it in the body. `FINDINGS:`: fix, rerun the reproduction each finding quotes and every criterion at the new head, push, and resume that reviewer subagent with `see <pr-url>`, launching a new one when it cannot be resumed and the pull request shows no verdict at the head yet. `APPROVED: <head>`: `merge`, running `merge.py <pr-url>` as a Bash call of its own, since an allow rule matches a compound command only when every part does; refused by GitHub, merge the default branch in, rerun every check on the merged tree, since a clean merge can still break a caller, push, and resume it the same way. Merged, which closes the task: `prompt` the leader `see <pr-url>`.

While your own reviewer or eval runs, wait in one bounded foreground Bash poll instead of stopping.
`APPROVED:` while the owner's sign-off is pending: push the pending commit, else `comment` `BLOCKED: owner review of <pr-url>`.

## Report

1. Do the work the task asks, then rerun every criterion and `comment` the report on the task as one comment: the findings, then the criteria table.
2. Launch the `reviewer` on that comment's url on Opus. `FINDINGS:`: fix, rerun every criterion, `comment` the report again, and resume that reviewer with `see <comment-url>`. `APPROVED: <comment-url>` naming your newest report: `resolve` the task, then `prompt` the leader `see <task-url>`.

# Work

Work one issue of a goal, as the worker its leader started.

1. Work in the issue's worktree, the one `git worktree list` names `*-<issue>`. `read` the issue and its parent, and `claim` the issue; held by another session, `comment` `WAITING: held by <branch>` on the issue and stop.
2. Write your mission, then review each criterion of the issue: one you cannot check, or that the honest empty outcome cannot pass, is a decision that is not yours.
3. Implement, then rerun every criterion, commit, push, and write the criteria table into the `pr` body, opening the `pr` at the first push; repeat per iteration. After 3 iterations without a criterion newly passing, `comment` `BLOCKED: stuck on <criterion>` and go on as for any decision that is not yours.
4. With every criterion passing, launch the reviewer `review-size.py origin/<default> HEAD` prints, `reviewer-small` for at most 20 changed lines and `reviewer` above, on the pull request's url, and name it in the body. `FINDINGS:`: fix, rerun the reproduction each finding quotes and every criterion at the new head, push, and resume that reviewer with `SendMessage` `see <pr-url>`, launching a new one when it cannot be resumed and the pull request shows no verdict at the head yet. `APPROVED: <head>`: `merge`; refused by GitHub, merge the default branch in, rerun every check on the merged tree, since a clean merge can still break a caller, push, and resume it the same way. Merged: `prompt` the leader `see <pr-url>` and delete your mission.

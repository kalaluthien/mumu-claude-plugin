# Work

Work one issue of a goal, as the worker its leader started; the issue is yours end to end.

1. Work in the issue's worktree, the one `git worktree list` names `*-<issue>`, and `name` yourself after it when you came from another issue. `read` the issue and its parent, and `claim` the issue; held by another session, `comment` that on the issue and stop.
2. Write your mission, then review each criterion of the issue: one you cannot check, or that the honest empty outcome cannot pass, is a decision that is not yours, below.
3. Implement, then rerun every criterion, commit, push, and write the criteria table into the `pr` body, opening the `pr` at the first push; repeat per iteration. After 3 iterations without a criterion newly passing, `comment` `BLOCKED: stuck on <criterion>` and go on as for any decision that is not yours.
   Split research, tests and review inside the issue with any subagent, but give two subagents at once different files, since they share your branch and one file edited twice is overwritten. Work that needs its own pull request is the leader's to `file` and `start`: ask for it as a decision that is not yours, below.
4. With every criterion passing, launch the reviewer `review-size.py origin/<default> HEAD` prints, `reviewer-small` for at most 20 changed lines and `reviewer` above, on the pull request's url, and name it in the body. `Findings`: fix, push, and resume that reviewer with `SendMessage` `see <pr-url>`, launching a new one when it cannot be resumed. `Approved <head>`: `merge`; refused by GitHub, merge the default branch in, push, and resume it the same way. Merged: `prompt` the leader `see <pr-url>` and delete your mission.
5. `SendMessage` the leader, at its name in `ListAgents`, one line: you are idle, and the pane to prompt, `$HERDR_PANE_ID`. Then wait: the leader answers with an assignment prompt, never a message.

Work that waits on another worker's (a merge, a name, an interface): `SendMessage` that worker, at its name in `ListAgents`, one line naming what you wait for and the url where it will land; when it lands there, that worker sends you `see <url>` the same way. The leader is not the relay, and the record stays on the issue or the pull request.

Consensus, with a worker under the same leader only (another leader's worker is reached through your leader): `comment` your proposal on your issue and `SendMessage` that worker `see <issue-url>`; it answers once there. Agreed: one of you `comment`s `Agreed: <result>` on one issue and links it from the other. After that one round without agreement, both escalate as below.

A decision that is not yours: `comment` `BLOCKED: <question>` on the issue, `prompt` the leader `see <issue-url>`, and stop until it prompts you back.

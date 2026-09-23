# Work

Work one issue of a goal, as the worker its leader started.

1. Work in the issue's worktree, the one `git worktree list` names `*-<issue>`, and `name` yourself after it when you came from another issue. `read` the issue and its parent, and `claim` the issue; held by another session, `comment` that on the issue and stop.
2. Write your mission.
3. Implement, run the repository's own checks, commit and push, and open the `pr` at the first push.
   Launch subagents only to split research or to edit different files at once in your worktree, since they share its branch and one file edited twice is overwritten. Work that needs its own pull request is the leader's to `file` and `start`: ask for it as a decision that is not yours, below.
4. Write the checks you ran into the `pr` body, then launch the reviewer `review-size.py origin/<default> HEAD` prints, `reviewer-small` for at most 20 changed lines and `reviewer` above, on the pull request's url, and name it in the body. `Findings`: fix, push, and resume that reviewer with `SendMessage` `see <pr-url>`, launching a new one when it cannot be resumed. `Approved <head>`: `merge`; refused by GitHub, merge the default branch in, push, and resume it the same way. Merged: `prompt` the leader `see <pr-url>` and delete your mission.
5. `SendMessage` the leader, at its name in `ListAgents`, one line: you are idle, and the pane to prompt, `$HERDR_PANE_ID`. Then wait: the leader answers with an assignment prompt, never a message.

Work that waits on another worker's (a merge, a name, an interface): `SendMessage` that worker, at its name in `ListAgents`, one line naming what you wait for and the url where it will land; when it lands there, that worker sends you `see <url>` the same way. The leader is not the relay, and the record stays on the issue or the pull request.

A decision that is not yours: `comment` `BLOCKED: <question>` on the issue, `prompt` the leader `see <issue-url>`, and stop until it prompts you back.

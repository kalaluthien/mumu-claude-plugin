You are a teamwork manager. Read `teamwork/skills/kick-off/references/manager.md` with the Read tool, and every file it links that a case needs. Act on nothing; only say how that playbook routes each case below.

For each case, give:

- `section`: `Steps` when a table under `## Steps` routes it, `Rules` when a bullet under `## Rules` routes it, `none` when nothing does.
- `locator`: for `Steps`, the first cell of the table row that routes it, copied exactly without the pipes; for `Rules`, the bold name of the bullet; else an empty string.
- `operations`: the operations the playbook has you do for it, in order, each as the backticked word the playbook uses (such as `file`, `decide`, `tell`, `reopen`, `resolve`, `close`, `start`, `ask`, `answer`, `notify`, `screen`, `read`, `list`, `edit`), or the tool name it names; an empty list when it has you only reply.

Cases:

1. `update-open-root`: the owner adds a requirement to an open root task that a worker holds.
2. `live-worker-work`: the owner comments on what a live worker is building right now.
3. `follow-up-closed`: the owner asks for more on work a closed root delivered.
4. `new-work`: the owner asks for new work in this project.
5. `other-project`: the owner asks for work in another project's repository.
6. `start-manager`: the owner asks to start a manager and names no work.
7. `endless-duty`: the owner asks for a session that keeps monitoring a page for changes.
8. `stop-work`: the owner says to stop a task that is in progress.
9. `tasks-pane`: the owner asks to show the Tasks pane again.
10. `remark`: the owner says thanks.
11. `prompt-covered`: a worker waits at a tool prompt whose action the owner already allowed in this conversation.
12. `prompt-uncovered`: a worker waits at a tool prompt the owner has not spoken to.
13. `work-style`: the owner tells how a worker should work, such as to commit more often.
14. `approved-follow-up`: the owner approves a follow-up the manager proposed.
15. `usage-limit`: the owner says the usage limit is near.
16. `owner-answer`: the owner answers a worker's question that only the owner could settle.
17. `batch-landed`: a worker reports a batch landed while its root's words are not all covered.
18. `status-check`: the owner asks how the work stands.
19. `progress-report`: a worker's change merged, and the owner is not asking anything.
20. `prompt-refused`: a worker waits at a tool prompt that the answering script refuses to answer.
21. `pause-idle`: during a pause for the usage limit, the heartbeat prints an `idle` line for a worker.

Then write the two replies the playbook has you give the owner for cases 18 and 19, each in the form the playbook sets for it, with this board: task "Route owner requests by one table", held by owner-router-worker, drafting a table, next a rebase, waiting on the task "Take each board write field as an option"; task "Take each board write field as an option", held by board-writes-worker, just merged, nothing next, waiting on nothing.

- `status-reply`: your reply to case 18.
- `progress-reply`: your reply to case 19.

End your answer with one fenced `json` block and nothing after it: an object with key `cases`, an object from each case's name to `{"section": …, "locator": …, "operations": […]}`, and keys `status-reply` and `progress-reply`, each a string.

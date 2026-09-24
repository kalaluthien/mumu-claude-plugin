# Stop

The owner stops the goal early.

1. `comment` `Stopped: <reason>` on each open issue, `gh pr ready --undo` its pull request, then `comment` the state on the parent: each issue, its pull request and what is left.
2. `close` each worker named in your mission.
3. Remove the goal from your mission; when no goal is left, delete it, which stops the `worker-watch` and `lead-heartbeat` monitors.
4. Leave the issues open unless the owner says to resolve them; then `resolve` each.

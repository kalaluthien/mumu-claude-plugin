# Stop

The owner stops a goal early.

1. `stop` each open task and goal under it, deepest first, then `comment` the state on the goal: each task, its pull request and what is left.
2. `close` each worker of those tasks in `live`.
3. `stop` the goal itself, unless the owner says to keep it open.

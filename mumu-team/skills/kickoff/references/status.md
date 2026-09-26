# Status

Report where a goal stands, changing nothing.

1. Find each goal: a goal or task url in the text, else the open root goals and root tasks, `gh issue list --state open --search "no:parent-issue label:kind:goal,kind:task" --json number,title,url`, with `--label scope:<folder>` added for a `<folder>-lead` run in your checkout, else ask with `AskUserQuestion`.
2. `read` each goal, then each goal and task under it and each task's pull request.
3. `live`, matching each worker to its task by its name `<topic>-<n>-<k>`.
4. Report one row per task: its state on GitHub, its pull request or report comment, and its worker's `agent_status`, or none.

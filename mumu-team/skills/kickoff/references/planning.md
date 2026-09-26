# Planning

File, reopen and split work, and ask the owner about it.

- Hold any number of root goals and root tasks at once; new work is led beside what you hold. File a goal only when it holds two or more tasks, related or not; one task is a root task, and a chore a root task at `effort:low`. A goal too large for one level is split into goals, never continued elsewhere.
- Before you `file` a goal or task, search the repository's issues, open and closed, with `gh issue list -R <repo> --state all --search <words>`: work of the same kind as a closed issue (#67 and #84 both hid a skill from the `/` menu) reopens it with `gh issue reopen`, widens its `## Definition of done` with `decide.py --criteria`, and is led from there under a new attempt, so its history stays in one place; otherwise file a new issue that links it.
- File the fewest tasks at the widest scope: work sharing a mechanism is one task, split by feature and never by layer, and a new finding or a review's defect widens the task it relates to. File them all, read their numbers back, then write the order and cross-references.
- A defect you find is fixed in the current work or filed as a task of the current goal with a worker, and you say which; noted on an issue with no owner, it is dropped.
- Research or exploratory work whose result later pull requests read is a task with a worker, driven one step per prompt, never a subagent whose result lives only in scratch.
- A hunch the owner asks you to interpret goes in as `reading: <yours>` beside their words, revisable, never as their decision.
- Ask the owner only architecture, infrastructure and user-experience questions, every one at once with `AskUserQuestion`, and have them confirm only those criteria; decide the rest and record it as `DECIDED:` on the goal.

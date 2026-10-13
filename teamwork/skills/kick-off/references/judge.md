# Judge

Review the tasks, the pull request or the report at the url or path you were given, which you did not write. Change nothing and post nothing: reply to your caller. The terms are [SKILL.md](../SKILL.md)'s.

1. **Read** what you review: a pull request's head sha and its diff from the merge base, `git fetch origin` then `git diff origin/<default>...<sha>`, and each touched file the diff needs as `git show <sha>:<path>`; or the tasks and their backlog; or a report and its issue.
2. **Tasks**: each clause of the backlog's words and of each `DECIDED:` has a criterion; run each `[check]` on the default branch as written: one that passes there, cannot run, or quotes no failing output is a gap; so are a `[score]` with no sample or margin and two open tasks touching the same files unordered.
3. **Change or report**: each `[check]` meets its pass condition at the head; each `[score]` is measured beside main, never quoted from an earlier run. The change does what its task asks and nothing else, breaks no caller or boundary input, has a check that fails without it, and is the simplest that does it, reading like the code around it; a report cites what backs each claim.
4. **Reply**: `approve <sha>`, the head sha read again just before, starting over if it moved, then one line on what you checked; or `fix <sha>`, then one line per gap: the criterion, the gap, and the direction of the fix, never its text. For tasks, `approve` or `fix` alone; for a report, its url instead of a sha.

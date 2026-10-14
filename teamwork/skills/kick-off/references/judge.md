# Judge

Review what your caller hands you, which you did not write, in [SKILL.md](../SKILL.md)'s terms; change nothing, post nothing, reply only to your caller.

1. **Read** it: tasks with their backlog; a change at its sha, by `git fetch origin`, `git diff origin/<default>...<sha>`, and `git show <sha>:<path>` for each file it needs; or a report with its issue.
2. **Find gaps**:

   | reviewing | a gap is |
   | --- | --- |
   | tasks | a clause of the backlog's words or of a `DECIDED:` with no criterion; a criterion not as SKILL.md defines it, each `[check]` run on the default branch as written; two open tasks touching the same files unordered |
   | a change, against its task's Definition of done however it lands | a `[check]` missing its pass condition at the head; a `[score]` not measured beside main now; work beyond or short of its task; a broken caller or boundary input; no check that fails without it; not the simplest change, or not reading like the code around it |
   | a report | a claim with no source cited |
3. **Reply** `approve` or `fix`, then the head sha read again just before (start over if it moved), a report's url, or for tasks no sha; then one line on what you checked, or per gap one line: the criterion, the gap, and the fix's direction, never its text.

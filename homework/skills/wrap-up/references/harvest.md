# Harvest

Keep what this session learned where the next agent will meet it. A lesson
handed over by a person skips to step 4.

1. List candidates since the last wrap-up: `<skill>/scripts/list-candidates.py`.
2. Over them and the session ask what was intended, what happened, why, and
   what to sustain or improve, then look through these lenses, each with the
   evidence that calls for it:
   - **Navigation**: finding a file or fact took long: a pointer where the search began.
   - **Checks**: a mistake a check could have caught: first read the repository's own check commands and CI, since one that exists but is unwired is the finding.
   - **Mechanical or judgement**: a fixed pattern (a banned call, a path rule) becomes a check, never a written rule; only a judgement call is written.
   - **Steering size**: an instruction file grown large: move detail out, behind a pointer.
   - **No-ops**: an instruction that changed no behaviour: cut it.
   - **Tool economy**: an expensive call that a cheaper command would answer.
   - **Information access**: a fact the agent could not reach: give it read access.
3. Draft each answer worth keeping, one per cause:
   - improve: "when <situation>, do <action>, because <the broken assumption>";
   - sustain, an owner-accepted choice or a detour that worked: "when <situation>, keep <action>, because <what it saved>";
   - a procedure worked out: its steps as run.
   Of n drafts keep all when n ≤ 3, else the 3 + (2(n−3)+2)//5 most severe, the costliest to repeat first, telling the owner how many were dropped.
4. Route each lesson to the first row it fits:

   | the lesson | destination |
   | --- | --- |
   | something a check could decide | a hook, script, lint rule or CI step, by [hook-authoring.md](hook-authoring.md) |
   | a procedure that worked again, or how a delegate should work | the skill that owns the work, by [skill-authoring.md](skill-authoring.md) |
   | true for every project: another project's memory holds it, or the user said it for all work | `<config>/CLAUDE.md`: an instruction and a clause of reason in its work's section; then delete this project's copy |
   | true for this project: a fact, a trap, a preference, a procedure that worked once | auto-memory, one memory file each |

5. Read every memory pool afresh, `<config>/projects/*/memory/`; a pool's key
   is its project's absolute path with each non-alphanumeric character as `-`,
   derived from the path, never back. Take the first operation that fits:
   - **Confirm**: an entry says it already: `<skill>/scripts/count-confirmations.py <file>`.
   - **Extend**: an entry on the same subject or mechanism: add to it.
   - **Add**: a new memory file with `confirmed: 1` and `last-confirmed: <today>` in its frontmatter, justified in one line: the nearest entry and why it could not be extended, or that none exists.

   Every memory file states when it applies and when it is wrong, as
   SKILL.md's memory file says. An extend or add cites evidence: a
   candidate's time, a url or a `path:line`.
6. Edit only the lines that change, `MEMORY.md` over a fresh read, since other
   sessions write it. Delete or correct any entry this session showed wrong.
7. A repeat an entry should have prevented: confirm it, and file a task in
   its project's issue tracker to make it a check or a skill step, naming
   which, the lesson and the repeat's evidence; with no tracker, tell the
   owner in one line.

Tell the owner each lesson filed: its operation, text and file, and an add's
one line; with none, say nothing.

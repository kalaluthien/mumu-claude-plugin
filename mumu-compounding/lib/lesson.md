# Lesson

File each lesson, handed over by the user or found by a harvest. A harvest
goes over the work since the last one: a surprise (a failed check, a refusal,
a step redone, a success by an unplanned path) becomes a rule to act on at a
task's start, "when <situation>, do <action>, because <the broken
assumption>", and a procedure you had to work out keeps its steps as run.

1. Search every project's auto-memory, `~/.claude/projects/*/memory/`, for
   the same lesson, and read what is there now. Pick the last row of the
   routing table in retro's `SKILL.md` it fits; when that row is this file, the last
   row of the table below. A pool's key is its project's absolute path with
   every character but a letter or digit as `-`, so derive the key from the
   path, never back.
2. Apply one operation to each entry you touch: ADD, EDIT (a near-duplicate
   too), DELETE, or NONE when it is already said. A lesson promoted to a
   later row deletes the entries it replaces in this project's pool only.
   Never rewrite a file to fold a lesson in; edit `MEMORY.md` one line at a time over a fresh read, since another
   session may write the same pool.
3. Delete or correct any entry this session showed wrong, touched or not.

Tell the owner each lesson filed: what it says and where; with none, say nothing.

| the lesson | destination |
| --- | --- |
| holds for this project: a fact, a trap, the user's preference, a procedure that worked once | auto-memory, one fact per file as the harness's memory instructions give it |
| holds for every project: another project's pool already holds it, or the user gave it for all work | `~/.claude/CLAUDE.md`: its sentence, one instruction and one clause of reason, in the section naming the work, never only a link, since an issue or file it names changes; then DELETE its copy in this project's pool |

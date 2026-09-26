# Memory

File one lesson, handed over by the user or found by a harvest.

1. Search every project's auto-memory, `~/.claude/projects/*/memory/`, for
   the same lesson. Pick the last row of the routing table in `SKILL.md`
   that it fits; when that row is this playbook, pick the last row of the
   table below that it fits, else file it by that row's playbook with
   steps 2-3 here. Read what is there now. A pool's key is its project's
   absolute path with every character but a letter or digit as `-`, so a
   worktree keys its own; derive the key from the path, never back.
2. Apply one operation to each entry you touch: ADD, EDIT <entry>, DELETE
   <entry>, or NONE when it is already said. A near-duplicate is an EDIT. A
   lesson promoted to a later row DELETEs the entries it replaces in this
   project's auto-memory, and leaves other projects' entries alone. Never
   rewrite a file to fold a lesson in, and edit `MEMORY.md` one line at a
   time over a fresh read, since another session may write the same pool.
3. Delete or correct any entry this session showed wrong, touched or not.

Tell the owner each lesson filed: what it says and where; with none, say nothing about the harvest.

| the lesson | destination | shape |
| --- | --- | --- |
| holds for this project: a fact, a trap, the user's preference, a procedure that worked once | auto-memory, the directory the harness names | one fact per file, as the harness's memory instructions give it |
| another project's auto-memory already holds it, or the user gave it for all work | memory: `~/.claude/CLAUDE.md` | one instruction and one clause of reason, in the section naming the work |

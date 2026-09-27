# Lesson

File each lesson, handed over by the user or found by a harvest: a harvest
runs Harvest, then Filing; a lesson handed over, Filing only. `<config>` is
the folder the owner names, else `${CLAUDE_CONFIG_DIR:-$HOME/.claude}`, and
`<plugin>` the folder above this file's `lib/`.

## Harvest

1. List the candidates since the last harvest, whole transcript and GitHub
   records: `<plugin>/scripts/takeaway.py candidates`, or with
   the transcript path the owner names.
2. Over them and the session, answer the four after-action questions: what
   was intended, what happened, why the gap, and what to sustain or improve.
   Each answer worth keeping is one draft: to improve, "when <situation>, do
   <action>, because <the broken assumption>"; to sustain, a step or choice
   that worked, often one the owner accepted or a success by an unplanned
   path, "when <situation>, keep <action>, because <what it saved>"; a
   procedure you had to work out keeps its steps as run. Merge drafts of one
   cause. Each cites its evidence in every ADD or EDIT it becomes, an edit
   of an old entry too: a candidate's timestamp with its time, not a date
   alone, or its url, or a `path:line`.
3. Of n drafts file all when n ≤ 3, else the 3 + (2(n−3)+2)//5 that cost the
   most when repeated, and tell the owner in one line how many were dropped.

## Filing

1. Search every pool, `<config>/projects/*/memory/`, for the same lesson,
   and read what is there now. Pick the last row of the
   routing table in retro's `SKILL.md` it fits; when that row is this file, the last
   row of the table below. A pool's key is its project's absolute path with
   every character but a letter or digit as `-`, so derive the key from the
   path, never back.
2. Apply one operation to each entry you touch: ADD, with `confirmed: 1` and
   `last-confirmed: <today>` in its frontmatter; EDIT (a near-duplicate too);
   DELETE; CONFIRM, a memory file whose lesson was found again, through
   `<plugin>/scripts/confirmations.py confirm <file>`; or NONE
   for a sentence of `<config>/CLAUDE.md` already saying it. A lesson promoted to a
   later row deletes the entries it replaces in this project's pool only.
   Never rewrite a file to fold a lesson in; edit `MEMORY.md` one line at a time over a fresh read, since another
   session may write the same pool.
3. A surprise a lesson already on file should have prevented: CONFIRM it,
   and promote it through `/mumu-team:handoff`: a task, in the GitHub
   repository of its project, whose path is the `cwd` of a transcript in its
   pool's folder, to turn the lesson into a hook or a skill step, naming
   which, the lesson and the repeat's evidence. A project with no GitHub repository gets no task: tell the owner
   in one line instead.
4. Delete or correct any entry this session showed wrong, touched or not.

Tell the owner each lesson filed: what it says and where; with none, say nothing.

| the lesson | destination |
| --- | --- |
| holds for this project: a fact, a trap, the user's preference, a procedure that worked once | auto-memory, one fact per file as the harness's memory instructions give it |
| holds for every project: another project's pool already holds it, or the user gave it for all work | `<config>/CLAUDE.md`: its sentence, one instruction and one clause of reason, in the section naming the work, never only a link, since an issue or file it names changes; then DELETE its copy in this project's pool |

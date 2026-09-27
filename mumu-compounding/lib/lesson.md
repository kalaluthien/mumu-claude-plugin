# Lesson

A lesson handed over goes to Filing; a harvest runs Harvest first.
`<config>` is the folder the owner names, else
`${CLAUDE_CONFIG_DIR:-$HOME/.claude}`; `<plugin>` is the folder above `lib/`.

## Harvest

1. List candidates since the last harvest:
   `<plugin>/scripts/takeaway.py candidates [<transcript>]`.
2. Over them and the session ask what was intended, what happened, why,
   and what to sustain or improve. Each answer worth keeping is a draft,
   one per cause:
   - improve: "when <situation>, do <action>, because <the broken assumption>";
   - sustain, such as an owner-accepted choice or a detour that worked:
     "when <situation>, keep <action>, because <what it saved>";
   - a procedure worked out: its steps as run.
3. Of n drafts keep all when n ≤ 3, else the 3 + (2(n−3)+2)//5 costliest to
   repeat, telling the owner how many were dropped.

## Filing

1. Route each lesson to the last row it fits of retro's `SKILL.md` table,
   then, when that row is this file, of the table below.
2. Read every pool, `<config>/projects/*/memory/`, afresh. A pool's
   key is its project's absolute path, each non-alphanumeric character as
   `-`: derive it from the path, never back.
3. Take the first operation that fits:
   - CONFIRM, an entry says it already:
     `<plugin>/scripts/confirmations.py confirm <file>`, or NONE for a
     sentence of `<config>/CLAUDE.md`;
   - EDIT, an entry on the same subject or mechanism: extend it;
   - ADD, a file with `confirmed: 1` and `last-confirmed: <today>` in its
     frontmatter, justified in one line: the nearest entry and why it could
     not be extended, or that none exists.

   An ADD or EDIT cites evidence: a candidate's time, not date alone, a url
   or a `path:line`.
4. Edit only the lines that change instead of rewriting a file, `MEMORY.md`
   over a fresh read, since other sessions write it.
5. DELETE or correct any entry this session showed wrong; a lesson moved to
   a later row DELETEs what it replaces in this project's pool.
6. A repeat an entry should have prevented: CONFIRM it, and
   `/mumu-team:handoff` a task to its project's GitHub repository, a
   transcript's `cwd` in its pool's folder, to make it a hook or skill
   step, naming which, the lesson and the repeat's evidence; with no
   repository, tell the owner in one line.

Tell the owner each lesson filed: its operation, text and file, and an ADD's
one line; with none, say nothing.

| the lesson holds for | destination |
| --- | --- |
| this project: a fact, a trap, a preference, a procedure that worked once | auto-memory, one fact per file |
| every project: another project's pool holds it, or the user gave it for all work | `<config>/CLAUDE.md`: an instruction and a clause of reason, in its work's section, never only a link, which can change; then DELETE this project's copy |

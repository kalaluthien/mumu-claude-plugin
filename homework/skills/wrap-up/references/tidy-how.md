# Tidy

1. **Bound**: judge from this session's own instructions whether it may
   change memory and shared files. Bound to one task or scope, it may not:
   stop here, changing nothing, with one line saying why.
2. **Back up**: copy each memory folder not under version control to
   `<data>/backup/<today>/` before changing it, since a merge or a delete
   there cannot be undone.
3. **Find**: run `<skill>/scripts/list-drift.py <config>`, then read every
   target, routing each entry through [harvest.md](harvest.md)'s step 4 table.
4. **Fix in order**, so each conflict is judged once:
   1. **Duplicates**: one lesson in several places is kept in one; two entries on one subject or mechanism become one, keeping the shared procedure and dropping one-off ids, dates and paths.
   2. **Contradictions**: of two entries that conflict, keep the one with newer evidence; with none either way, leave the conflict for the owner.
   3. **Superseded**: an entry a later one restates, narrows or reverses is rewritten or deleted.
   4. **Stale**: check each path, command, flag or package an entry names with a read-only probe (list, search, `--help`); fix it when the new target is plain, else leave it for the owner.
   5. **Placement**: a lesson a file should hold moves there and its entry is deleted; an instruction line that restates what the repository shows is cut, its non-standard rules kept; a document for people keeps its overview.
   6. **Size**: an index past its load limit is cut to one line per entry; a skill grown past a few focused parts is split, not extended.
5. **Obvious only**: apply a fix at once when the steps above give it and it
   is small; a change to a skill, hook or script counts only when its own
   check still passes after it.
6. **Leave the rest**: a fix that is not obvious or is large, or a lesson
   `list-drift.py` lists as never found again, goes as one issue in the
   repository that owns the file, labelled `backlog`, its body naming each
   file, reason and cost, `<n> files, <m> lines`, never a memory file's body.
   A pool with no repository: list the fix and its cost in the final message.
7. **Report** each fix applied, each issue's url and each fix left; with none
   found, say so.

---
name: dream
description: Use when the Stop hook asks for a dream, or when auto-memory pools have drifted - a MEMORY.md link to a missing file, a memory file no index lists, two files of one name, one lesson saved in several places, a lesson a skill, agent or hook should hold - applying the obvious fixes itself and filing the rest as a backlog issue. Not for filing one session's lessons (retro).
user-invocable: false
---

# dream

retro files lessons one session at a time; dream reviews what they built,
never waiting on an answer. Apply [lesson.md](${CLAUDE_PLUGIN_ROOT}/lib/lesson.md)'s
operations and destinations, reading its "this project" and "this session"
as every pool.

`<config>` is the folder the owner names, else `${CLAUDE_CONFIG_DIR:-$HOME/.claude}`.
The sources are its pools, `<config>/projects/*/memory/`, `<config>/CLAUDE.md`,
and in each pool's checkout, the folder whose path gives the pool's key,
the files holding lessons: `AGENTS.md`, `CLAUDE.md`, skills, agents,
references and hooks.

1. Judge from this session's own instructions whether it may change memory
   and shared files. Bound to one task or scope, it may not: end dream
   there, changing and filing nothing, with one line saying why.
2. List what the shell can find:

   ```sh
   root="<config>/projects" bash <<'SH'
   for pool in "$root"/*/memory; do
     grep -o '([^)]*\.md)' "$pool/MEMORY.md" 2>/dev/null | tr -d '()' | while read -r f; do
       [ -e "$pool/$f" ] || echo "dangling link: $pool/MEMORY.md -> $f"
     done
     for f in "$pool"/*.md; do
       [ -e "$f" ] || continue
       n=${f##*/}
       [ "$n" = MEMORY.md ] || grep -qF "($n)" "$pool/MEMORY.md" 2>/dev/null || echo "unindexed: $f"
     done
   done
   ls "$root"/*/memory | grep '\.md$' | grep -vx MEMORY.md | sort | uniq -d | sed 's/^/duplicate name: /'
   SH
   "${CLAUDE_PLUGIN_ROOT}/scripts/confirmations.py" stale "<config>"
   ```

3. Read every source, routing each entry through the table in
   [retro's SKILL.md](${CLAUDE_PLUGIN_ROOT}/skills/retro/SKILL.md). Apply
   each obvious fix at once: a dangling link's line dropped, an unindexed
   file indexed, an entry a repository file already states deleted, one
   lesson kept in several places kept in one (lesson.md's last row for
   pools), two entries on one subject or mechanism merged into one as
   lesson.md's EDIT extends an entry, a small lesson a file should hold added there and its entry
   deleted. A file in a checkout whose default branch is guarded changes
   the way that repository takes changes, as its `AGENTS.md` says.
4. A fix the table gives that is not obvious or is large, a lesson
   `stale` lists among them, waits on the owner: file it as one `backlog` issue in the
   repository that owns the file (`gh issue create -R <owner>/<repo>
   --label backlog`), its body naming each file, reason and cost, `<n>
   files, <m> lines`, never a memory file's body. A pool with no
   repository: name the fix and its cost in the final message instead,
   asking nothing.
5. Report each fix applied, each issue's url and each fix left; with none
   found, say so, offering no other change, and write nothing.

---
name: dream
description: Checks every auto-memory pool for broken index links, unindexed files, duplicate names and one lesson kept in several pools, then fixes only the ones the owner picks.
disable-model-invocation: true
---

# dream

retro files lessons one session at a time; dream reviews the pools they
built. Apply [lesson.md](${CLAUDE_PLUGIN_ROOT}/lib/lesson.md)'s operations
and destinations, reading its "this project" and "this session" as every pool.

`<config>` is the folder the owner names, else `${CLAUDE_CONFIG_DIR:-$HOME/.claude}`:
its pools are `<config>/projects/*/memory/`, and `<config>/CLAUDE.md` is the
file for every project.

1. List what the shell can find:

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
   ```

2. Read every pool's files, and find one lesson kept in two or more pools
   under any name: it holds for every project, so lesson.md's last row
   applies.
3. Nothing found: say so, and write nothing.
4. Otherwise put the fixes to the owner as one `AskUserQuestion`
   question, `multiSelect: true`, one option per fix: the top 4 by impact,
   each option's label the action (ADD, EDIT or DELETE) and file, its
   description the reason; a file and its `MEMORY.md` line are one fix. The
   options chosen are approved and the rest rejected; more than 4 fixes, name
   the rest in one line after the answer, left for the next `/dream`.
5. Apply only the approved fixes; a file only rejected fixes name is never
   touched. Report each fix applied or skipped.

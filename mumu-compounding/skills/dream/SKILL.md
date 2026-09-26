---
name: dream
description: Checks every auto-memory pool for broken index links, unindexed files, duplicate names and one lesson kept in several pools, then fixes only the rows the owner approves, each file backed up first.
disable-model-invocation: true
argument-hint: approve all but the rows on orphan.md
---

# dream

retro files lessons one session at a time; dream reviews the pools they
built. Apply [lesson.md](${CLAUDE_PLUGIN_ROOT}/lib/lesson.md)'s operations
and destinations, reading its "this project" and "this session" as every pool.

`<config>` is the folder the owner names, else `${CLAUDE_CONFIG_DIR:-$HOME/.claude}`:
its pools are `<config>/projects/*/memory/`, and `<config>/CLAUDE.md` is the
file for every project. `<backup>` is the new or empty folder the owner
names, else `${CLAUDE_PLUGIN_DATA}/dream/<utc time>/`.

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
4. Otherwise show one table, a row per fix: number, action (ADD, EDIT or
   DELETE), file, reason; a file and its `MEMORY.md` line are one row. Apply
   only the rows the owner approves, with `/dream` or after the table; a file
   only rejected rows name is never touched.
5. Before each write to a file, copy it to the same path under `<backup>` as
   under `<config>`; a failed copy skips its row.
6. Report each row applied or skipped, and for each file backed up the
   command that restores it, `cp '<backup copy>' '<file>'`.

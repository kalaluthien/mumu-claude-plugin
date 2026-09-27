---
name: dream
description: Use when the Stop hook asks for a dream, or when auto-memory pools have drifted - a MEMORY.md link to a missing file, a memory file no index lists, two files of one name, one lesson saved in several projects' pools, a lesson a skill, agent or hook should hold - fixing only what the owner picks. Not for filing one session's lessons (retro).
user-invocable: false
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
   "${CLAUDE_PLUGIN_ROOT}/scripts/confirmations.py" stale "<config>"
   ```

2. Read every pool's files, and route each entry through the table in
   [retro's SKILL.md](${CLAUDE_PLUGIN_ROOT}/skills/retro/SKILL.md), which
   gives these fixes:
   - one lesson kept in two or more pools under any name: it holds for every
     project, so lesson.md's last row applies;
   - a lesson a skill, a references file, an agent or a hook should hold:
     EDIT that file, adding the lesson as a step or rule where it applies,
     and DELETE the pool entry once the file states it; in a git checkout
     whose default branch a hook guards, as in a project a mumu-team lead
     holds, hand the edit, naming the file and the lesson, to that
     project's lead through `/mumu-team:handoff` instead, and the entry
     goes at a later round that finds it stated;
   - an entry the repository already states: DELETE it;
   - a lesson `stale` lists, never found again in 60 days: DELETE it, at
     the cost that line prints, only when the owner picks it.
3. No fix found that was not rejected in this call: say so, with the
   fixes applied in earlier rounds, and stop, offering no other change;
   in the first round, write nothing.
4. Otherwise put the fixes not yet rejected in this call to the owner as
   one `AskUserQuestion` question, `multiSelect: true`, one option per fix:
   the top 4 by impact, each option's label the action (ADD, EDIT or
   DELETE) and file, its description the reason and its cost, `<n> files,
   <m> lines` touched; a file and its
   `MEMORY.md` line are one fix, and so are a lesson moved and the copies
   it replaces. The tool takes 2 to 4 options, so a lone fix gets a
   second option, `None`. The options chosen are approved and the rest
   rejected.
5. Apply only the approved fixes; a file only rejected fixes name is never
   touched, and nothing is handed off that was not chosen. Report each fix
   applied or skipped.
6. Go back to step 1: one dream runs rounds until step 3 stops it.

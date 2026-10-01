---
name: dream
description: Use when the Stop hook asks for a dream, or when auto-memory pools have drifted - a MEMORY.md link to a missing file, a memory file no index lists, two files of one name, one lesson saved in several projects' pools, a lesson a skill, agent or hook should hold - fixing each itself and leaving only a stale lesson's deletion to the owner's tick on a GitHub issue. Not for filing one session's lessons (retro).
user-invocable: false
---

# dream

retro files lessons one session at a time; dream reviews the pools they
built. Apply [lesson.md](${CLAUDE_PLUGIN_ROOT}/lib/lesson.md)'s operations
and destinations, reading its "this project" and "this session" as every pool.
Dream never waits on an answer: it applies every fix but a stale lesson's
deletion, and leaves that one for the owner to tick on an issue.

`<config>` is the folder the owner names, else `${CLAUDE_CONFIG_DIR:-$HOME/.claude}`:
its pools are `<config>/projects/*/memory/`, and `<config>/CLAUDE.md` is the
file for every project. `<repo>` is the repository the owner names, else
`kalaluthien/mumu-claude-plugin`. The open `Confirm dream fixes` issue, when
there is one, is the url in `<config>/dream-issue.txt`; its body is one
`- [ ]` line per fix waiting on the owner: `- [ ] DELETE
projects/<pool>/memory/<file>: <reason>; <n> files, <m> lines`. The
repository is public, so a line never quotes a memory file's body nor a
path outside `projects/<pool>/memory/`.

1. With `<config>/dream-issue.txt` present, read the issue:
   `gh issue view <url> --json state,body`. Closed: remove the file.
   Open: apply each ticked `- [x]` fix, and drop its line and each line
   whose file is gone; with no line left, `gh issue close <url>` and remove
   the file, else `gh issue edit <url> --body-file <body>`.
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

3. Read every pool's files, and route each entry through the table in
   [retro's SKILL.md](${CLAUDE_PLUGIN_ROOT}/skills/retro/SKILL.md), which
   gives these fixes:
   - a dangling link: DELETE the `MEMORY.md` line; a file no index lists:
     ADD its `MEMORY.md` line, unless another fix below removes it;
   - one lesson kept in two or more pools under any name: it holds for every
     project, so lesson.md's last row applies;
   - a lesson a skill, a references file, an agent or a hook should hold:
     EDIT that file, adding the lesson as a step or rule where it applies,
     and DELETE the pool entry once the file states it; in a git checkout
     whose default branch a hook guards, as in a project a teamwork lead
     holds, hand the edit, naming the file and the lesson, to that
     project's lead through `/teamwork:handoff` instead, and the entry
     goes at a later round that finds it stated;
   - an entry the repository already states: DELETE it;
   - a lesson `stale` lists, never found again in 60 days: DELETE it, at
     the cost that line prints, only once the owner ticks it on the issue.
4. No fix found: say so, with the fixes applied in earlier rounds, and
   stop; in the first round, write nothing.
5. Apply each fix but a stale lesson's deletion; a file and its `MEMORY.md`
   line are one fix, and so are a lesson moved and the copies it replaces.
   Put each stale deletion not on the issue yet as a line there: edit the
   open issue's body, else write the body to a file and
   `gh issue create -R <repo> --title "Confirm dream fixes" --label backlog --label scope:homework --body-file <body>`,
   writing the url it prints to `<config>/dream-issue.txt`.
6. Report each fix applied, and the issue's url when it has lines. When this
   session's own instructions have it report its work to another session,
   tell that session the url the way they say, and go on without waiting.
7. Go back to step 2: one dream runs rounds until step 4 stops it, a fix
   already on the issue counting as none found.

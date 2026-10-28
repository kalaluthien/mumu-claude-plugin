# Dream

Tidy what earlier sessions kept: find the drift in each target below, then fix it in the order the steps give.

## Domain

What a dream reads, found afresh in the project at hand: list what exists with `git ls-files` and a glob, never assume a layout.

| target | where it lives | drift to look for |
| --- | --- | --- |
| Claude memory: instruction files | `AGENTS.md` and `CLAUDE.md` from the project root down, `.claude/rules/`, `<config>/CLAUDE.md` and `<config>/rules/` | a rule stated twice, rules that contradict, a line that restates what the repository shows, a path or command that no longer exists |
| Claude memory: auto-memory | this project's pool, `<config>/projects/<key>/memory/`, and any pool holding a copy of one of its lessons | what `${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-drift.py` prints; one lesson in several files or pools; an entry a later one replaces; a lesson an instruction file or skill should hold |
| project documents | `README.md` and the other documents the repository keeps for people, such as `docs/` and `CONTRIBUTING.md` | a step, file or command the repository no longer has; two documents that disagree |
| project skills | `.claude/skills/*/SKILL.md` and the skills of plugins the repository owns, with their references and scripts | a description that overlaps another skill's, a skill grown past a few focused parts, a skill whose commands fail |

## Steps

1. **Bound**: judge from this session's own instructions whether it may change memory and shared files. Bound to one task or scope, it may not: stop here, changing nothing, with one line saying why.
2. **Back up**: copy each memory folder not under version control to `<data>/backup/<today>/` before changing it, since a merge or a delete there cannot be undone.
3. **Find**: run `${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-drift.py <config>`, then read every target, routing each entry through [retro.md](retro.md)'s step 4 table.
4. **Fix in order**, so each conflict is judged once:
   1. **Duplicates**: one lesson in several places is kept in one; two entries on one subject or mechanism become one, keeping the shared procedure and dropping one-off ids, dates and paths.
   2. **Contradictions**: of two entries that conflict, keep the one with newer evidence; with none either way, keep the more specific one (the repository's own rule over a global one) and say so in the report.
   3. **Superseded**: an entry a later one restates, narrows or reverses is rewritten or deleted.
   4. **Stale**: check each path, command, flag or package an entry names with a read-only probe (list, search, `--help`); fix it when the new target is plain, else delete the entry.
   5. **Placement**: a lesson a file should hold moves there and its entry is deleted; an instruction line that restates what the repository shows is cut, its non-standard rules kept; a document for people keeps its overview.
   6. **Size**: an index past its load limit is cut to one line per entry; a skill grown past a few focused parts is split, not extended.
5. **Apply on your own**: apply each fix to this project's memory the steps above give at once, large ones too, since the backup makes it undoable. A fix to `<config>/CLAUDE.md`, another project's memory, a skill, a hook or a script goes as a patch, as [retro.md](retro.md) step 4 says. A patch to a skill, hook or script names the check that must still pass once applied.
6. **Leave the rest**: a fix the steps do not give, one that widens a permission or a guard, or a lesson `list-drift.py` lists as never found again, goes as one issue. File it in the repository that owns the file, labelled `backlog`. Its body names each file, reason and cost, `<n> files, <m> lines`, never a memory file's body. The filing asks first, and files only on the person's yes. A pool with no repository: list the fix and its cost in the final message.
7. **Report** each fix applied, each patch with its `! git -C <root> apply <patch file>` line, each issue's url and each fix left; with none found, say so.

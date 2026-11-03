# Dream

Tidy what earlier sessions kept: find the drift in each target below, fix it in the order the steps give, then keep the memory that best spares the owner's corrections when replayed on every project's history, after Dream-RSI (https://arxiv.org/html/2609.14858v1).

## Domain

What a dream reads, found afresh in the project at hand: list what exists with `git ls-files` and a glob, never assume a layout.

| target | where it lives | drift to look for |
| --- | --- | --- |
| Claude memory: instruction files | `AGENTS.md` and `CLAUDE.md` from the project root down, `.claude/rules/`, `<config>/CLAUDE.md` and `<config>/rules/` | a rule stated twice, rules that contradict, a line that restates what the repository shows, a path or command that no longer exists |
| Claude memory: auto-memory | `<home>` and this repository's folder `<home>/<repo>/`, else this project's pool, and any folder holding a copy of one of its lessons | what `${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-drift.py` prints; one lesson in several files or folders; an entry a later one replaces; a lesson an instruction file should hold; a lesson in `<home>` true for one repository only, or in a repository's folder true for every project; a file marked `skill:` |
| project documents | `README.md` and the other documents the repository keeps for people, such as `docs/` and `CONTRIBUTING.md` | a step, file or command the repository no longer has; two documents that disagree |
| project skills | `.claude/skills/*/SKILL.md` and the skills of plugins the repository owns, with their references and scripts | a description that overlaps another skill's, a skill grown past a few focused parts, a skill whose commands fail |

- **Replay case**: one owner correction dejavu recorded in any project, `<data>/dejavu/friction.jsonl`, shown to a pick judge only as the session up to it; the newest fifth is held out, never shown while revising.
- **Candidate**: one version of the memory home, a folder `<data>/dejavu/candidates/<name>/`: `current`, a copy as it is, and each revision `r<n>`.
- **Pick**: the memory files a candidate's index makes an agent open at a case, `<data>/dejavu/picks/<name>/<k>.jsonl`.
- **Mark**: a judge's verdict, with the owner's words in view, on the instruction files of a case, which load alike for every candidate, and on each set of picked files: covered, when they tell the action the owner wanted, or misfired, when one pushes the action the owner objected to; `<data>/dejavu/marks/<name>-<k>.jsonl`, `<name>` the candidate whose picks the round marks, so no round overwrites another's.

## Steps

1. **Bound**: judge from this session's own instructions whether it may change memory and shared files. Bound to one task or scope, it may not: stop here, changing nothing, with one line saying why.
2. **Back up**: copy each memory folder not under version control to `<data>/backup/<today>/` before changing it, since a merge or a delete there cannot be undone.
3. **Find**: run `${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-drift.py <config>`, then read every target, routing each entry through [retro.md](retro.md)'s step 4 table.
4. **Fix in order**, so each conflict is judged once:
   1. **Duplicates**: one lesson in several places is kept in one; two entries on one subject or mechanism become one, keeping the shared procedure and dropping one-off ids, dates and paths.
   2. **Contradictions**: of two entries that conflict, keep the one with newer evidence; with none either way, keep the more specific one (the repository's own rule over a global one) and say so in the report.
   3. **Superseded**: an entry a later one restates, narrows or reverses is rewritten or deleted.
   4. **Stale**: check each path, command, flag or package an entry names with a read-only probe (list, search, `--help`); fix it when the new target is plain, else delete the entry.
   5. **Placement**: a lesson a file should hold moves there and its entry is deleted; a lesson in the wrong memory folder moves by `${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/move-memory.py <file> <folder>`; an instruction line that restates what the repository shows is cut, its non-standard rules kept; a document for people keeps its overview.
   6. **Size**: an index past its load limit is cut to one line per entry; a skill grown past a few focused parts is split, not extended.
5. **Apply on your own**: apply each fix to this project's memory the steps above give at once, large ones too, since the backup makes it undoable. A fix to `<config>/CLAUDE.md`, another project's memory, a skill, a hook or a script goes as a patch, as [retro.md](retro.md) step 4 says. A patch to a skill, hook or script names the check that must still pass once applied.
6. **Replay**: keep the memory content that scores best on every project's corrections:
   1. Run `${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-replay-cases.py <data>/dejavu`; with no case, skip this step with one line why.
   2. Delete `<data>/dejavu/candidates/`, `<data>/dejavu/picks/` and `<data>/dejavu/marks/`, then copy `<home>` to `<data>/dejavu/candidates/current/`.
   3. Pick for a candidate: create `<data>/dejavu/picks/<name>/`, then for each `batch` line, start one `Agent` with `model: haiku`, all in one message, prompted: `Read ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/references/dream/replay-brief.md, then pick for candidate <data>/dejavu/candidates/<name> into <data>/dejavu/picks/<name>/<k>.jsonl on these cases: <the batch's case lines>`.
   4. Mark the candidate just picked, `<name>`: create `<data>/dejavu/marks/`, run `${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/list-recall-sets.py <data>/dejavu`, then for each `batch` line, start one `Agent` with `model: haiku`, all in one message, prompted: `Read ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/references/dream/mark-brief.md, then mark into <data>/dejavu/marks/<name>-<k>.jsonl these cases: <the batch's case, instructions and set lines>`.
   5. Revise: start one `Agent`, prompted: `Read ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/references/dream/revise-brief.md, then write candidate r<n> from <last> in <data>/dejavu with the scripts in ${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts`, `<last>` the candidate marked last, since this session has read the held-out owner words in 4 and a fresh one sees only the tuning cases. Pick and mark `r<n>` as in 3 and 4. Write at most two revisions, since each costs a round of judges.
   6. Run `${CLAUDE_PLUGIN_ROOT}/skills/wrap-up/scripts/score-memory.py <data>/dejavu`; while it prints a `missing:` line, a judge skipped a case: pick again in 3 the cases with no pick, mark again in 4, and run it again. Then act on its last line: apply each change of the selected revision to `<home>` file by file, over a fresh read, since other sessions write it meanwhile, as step 5 lets you; keep `current` unchanged.
7. **Skill lessons**: for each memory file marked `skill:`, ask the owner, one at a time, with its lesson and the skill it names: write it, keep it in memory, or drop it. On write, write it into that skill as a patch by [harness-authoring.md](harness-authoring.md), or, for a skill of another repository's plugin, as a `backlog` issue there, then delete the memory file and its index line; on drop, delete them; on keep, change nothing.
8. **Leave the rest**: a fix the steps do not give, one that widens a permission or a guard, or a lesson `list-drift.py` lists as never found again, goes as one issue. File it in the repository that owns the file, labelled `backlog`. Its body names each file, reason and cost, `<n> files, <m> lines`, never a memory file's body. The filing asks first, and files only on the owner's yes. A pool with no repository: list the fix and its cost in the final message.
9. **Report** the replay score table and the version kept, each fix applied, each skill lesson's answer, each patch with its `! git -C <root> apply <patch file>` line, each issue's url and each fix left; with none found, say so.

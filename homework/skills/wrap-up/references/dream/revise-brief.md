# Revise brief

You write one revision of memory from the owner corrections the last candidate missed, seeing only the tuning cases, so the held-out ones can still test it. A case line reads `case <id> <uncovered|misfire|missing> folder <folder>: <what went wrong> | owner: <quote> | recalled: <files>`.

## Steps

1. Copy `<dejavu>/candidates/<last>/` to `<dejavu>/candidates/<new>/`, the names you are given.
2. Run `<scripts>/list-tuning-marks.py <dejavu> <last>`, the scripts folder you are given; with a `missing` case, stop and reply that the judges must run again.
3. Change `<new>`, in the case's folder, `-` meaning the root:
   - an `uncovered` case extends the entry on its subject, or sharpens the index line that should have recalled it, and adds a file only when no entry fits;
   - a `misfire` narrows or deletes the entry among its recalled files that pushed the objected action.
4. Reply with one line per file changed: its path and what changed.

## Rules

- **Tuning only**: read no case but the script's lines, never `friction.jsonl` or `marks/`, since they hold the held-out cases.
- **Lessons, not answers**: write what to do in the situation, with no case id or quote, since a later session meets a new case.
- **Instruction files rule**: restate nothing the config's or a repository's `CLAUDE.md`, `AGENTS.md` or rules say, since those load anyway.
- **New only**: write only in `<new>`.

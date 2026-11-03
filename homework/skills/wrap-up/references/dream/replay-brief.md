# Replay brief

You judge whether one version of memory, a candidate, would have spared the owner each correction in a batch of replay cases. A case line reads `case <id> <repo> <split> folder <folder>: <what went wrong> | owner: <quote>`: what the agent did, then the owner's words against it.

## Steps

1. `Read` `<candidate>/MEMORY.md`, and `<candidate>/<folder>/MEMORY.md` for each case's folder other than `-`: the index lines that load before an agent acts.
2. For each case, picture the agent at the moment before its mistake, the owner's words not yet said, and pick the index lines whose situation fits that moment. `Read` each file a picked line links to.
3. Mark the case:
   - `covered`: a picked file tells the action the owner asked for;
   - `misfire`: a picked file pushes the action the owner objected to.
4. `Write` `<judgements>/<batch>.jsonl`, the folder and batch number you are given, one line per case:

   ```json
   {"case": "<id>", "covered": true, "misfire": false, "recalled": ["<file>"]}
   ```

5. Reply with one line: how many cases you judged, covered and misfired.

## Rules

- **Index first**: read only the candidate's indexes and the files you pick from them, never another file of the candidate or any other memory, since an agent meets only what its index makes it open.
- **Pick before you know**: pick lines from the part before `| owner:` alone, and use the owner's quote only to mark the case, since the agent never saw the quote first.
- **Every case**: write a line for every case you are given, `"covered": false` when nothing fits; a missing line counts as not covered.
- **Read only**: change no file but your verdict file.

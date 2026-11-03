# Replay brief

You pick, for each replay case in a batch, the memory files one version of memory, a candidate, would make an agent open at that moment. A case line reads `case <id> <repo> <split> folder <folder>: asked: <the person's last prompt> | then: <what the agent did after it>`: the session up to the moment the owner spoke next.

## Steps

1. `Read` `<candidate>/MEMORY.md`, and `<candidate>/<folder>/MEMORY.md` for each case's folder other than `-`: the index lines that load before an agent acts.
2. For each case, picture the agent at that moment and pick the index lines whose situation fits it; `Read` each file a picked line links to, and keep it when it bears on what the agent does next.
3. `Write` `<picks>/<batch>.jsonl`, the folder and batch number you are given, one line per case, each file relative to the candidate:

   ```json
   {"case": "<id>", "recalled": ["<file>"]}
   ```

4. Reply with one line: how many cases you judged, and how many recalled a file.

## Rules

- **Index first**: read only the candidate's indexes and the files you pick from them, never another file of the candidate or any other memory, since an agent meets only what its index makes it open.
- **Every case**: write a line for every case you are given, `"recalled": []` when nothing fits; a missing line counts as not covered.
- **Read only**: change no file but your picks file.

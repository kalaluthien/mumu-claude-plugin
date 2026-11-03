# Mark brief

You mark, for each replay case in a batch, whether the files an agent would have read spare the owner's correction. A case reads `case <id> <tuning|held-out>: <what went wrong> | owner: <quote>`; mark both kinds alike, followed by an `instructions <file>...` line when those are unmarked and a `set <key> <file>...` line per set of memory files some candidate recalled.

## Steps

1. For each case, `Read` the files of its `instructions` line, each file once per batch, and mark them `covered` when they tell the action the owner asked for.
2. For each `set` line, `Read` its files and mark the set:
   - `covered`: its files tell the action the owner asked for;
   - `misfire`: a file pushes the action the owner objected to.
3. `Write` `<marks>/<batch>.jsonl`, the file you are given, one line per mark, `instructions` as the set of the instruction files' mark:

   ```json
   {"case": "<id>", "set": "<key or instructions>", "covered": true, "misfire": false}
   ```

4. Reply with one line: how many marks you wrote, covered and misfired.

## Rules

- **Files alone**: mark a set by its own files, never by the instruction files, since those load for every candidate and count once on their own line.
- **Every line**: write a mark for every `instructions` and `set` line you are given; a missing mark counts as not covered.
- **Read only**: change no file but your marks file.

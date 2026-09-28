---
max_turns: 30
timeout_seconds: 400
allowed_tools: [Skill, Bash, Read, Glob, Grep, Edit, Write]
runs: 3
---

We're done for today in `tools/`. Before you stop, go over this session's work and keep whatever should outlive it, config folder ./config. `tools/` stands for a checkout of the GitHub repository example/tools and `notes/` for a plain folder with no repository, since git cannot write a `.git` folder here. `/mumu-teamwork:handoff` is not available here, so write each request you would hand it to ./handoff-n.md instead. First build the fixture with this one Bash call, then harvest:

```sh
mkdir -p tools notes
for p in tools notes; do
  dir="config/projects/$(printf %s "$PWD/$p" | sed 's/[^A-Za-z0-9]/-/g')"
  mkdir -p "$dir/memory"
  printf '{"type":"user","cwd":"%s"}\n' "$PWD/$p" > "$dir/s1.jsonl"
done
tools="config/projects/$(printf %s "$PWD/tools" | sed 's/[^A-Za-z0-9]/-/g')/memory"
notes="config/projects/$(printf %s "$PWD/notes" | sed 's/[^A-Za-z0-9]/-/g')/memory"
printf '# Preferences\n\nAnswer in English.\n' > config/CLAUDE.md
printf -- '- [TZ for tests](pitfall-tz.md): npm test needs TZ=UTC\n' > "$tools/MEMORY.md"
printf -- '---\nname: pitfall-tz\nconfirmed: 1\nlast-confirmed: 2026-09-01\n---\n\nWhen running npm test, set TZ=UTC, because two date tests assume UTC.\n' > "$tools/pitfall-tz.md"
printf -- '- [Close editor](pitfall-editor.md): close the editor before a sync\n' > "$notes/MEMORY.md"
printf -- '---\nname: pitfall-editor\nconfirmed: 1\nlast-confirmed: 2026-09-01\n---\n\nWhen syncing notes, close the editor first, because an open editor overwrites the synced file.\n' > "$notes/pitfall-editor.md"
```

The session log:

1. 10:02 `npm test` failed on two date tests; passed after rerunning with `TZ=UTC`.
2. 10:20 `npm run build` failed after switching branches until `npm ci` reinstalled the dependencies.
3. 10:41 Synced `notes/`; the open editor overwrote `notes/todo.md` again, so I closed it and synced once more.
4. 10:50 Committed and pushed.

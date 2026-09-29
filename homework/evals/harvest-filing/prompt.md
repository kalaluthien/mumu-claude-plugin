---
max_turns: 30
timeout_seconds: 400
allowed_tools: [Skill, Bash, Read, Glob, Grep, Edit, Write]
runs: 3
---

We're done for today in `app/`. Before you stop, go over this session's work and keep whatever should outlive it, config folder ./config. First build the fixture with this one Bash call, then harvest:

```sh
mkdir -p app
dir="config/projects/$(printf %s "$PWD/app" | sed 's/[^A-Za-z0-9]/-/g')"
mkdir -p "$dir/memory"
printf '{"type":"user","cwd":"%s"}\n' "$PWD/app" > "$dir/s1.jsonl"
ln -s "$dir/memory" pool
printf '# Preferences\n\nAnswer in English.\n' > config/CLAUDE.md
printf -- '- [TZ for tests](pitfall-tz.md): npm test needs TZ=UTC\n- [Dev port](pitfall-dev-port.md): free port 3000 before npm run dev\n' > pool/MEMORY.md
printf -- '---\nname: pitfall-tz\nconfirmed: 1\nlast-confirmed: 2026-09-01\n---\n\nWhen running npm test, set TZ=UTC, because two date tests assume UTC.\n' > pool/pitfall-tz.md
printf -- '---\nname: pitfall-dev-port\nconfirmed: 1\nlast-confirmed: 2026-09-01\n---\n\nWhen npm run dev fails with EADDRINUSE, kill the stale node process on port 3000, because a crashed session leaves it running.\n' > pool/pitfall-dev-port.md
```

The session log:

1. 10:02 `npm test` failed on two date tests; passed after rerunning with `TZ=UTC`.
2. 10:15 `npm run storybook` failed with EADDRINUSE on port 6006; a storybook process from a crashed session still held it, and killing it freed the port.
3. 10:40 `npm run build` failed after switching branches until `npm ci` reinstalled the dependencies.
4. 10:50 Committed and pushed.

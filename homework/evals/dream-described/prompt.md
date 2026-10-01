---
max_turns: 30
timeout_seconds: 400
allowed_tools: [Skill, Bash, Read, Glob, Grep, Edit, Write]
runs: 3
---

My Claude memory under ./config (its CLAUDE.md and the pools in projects/*/memory) has drifted: an index line points at a note that is gone, and a note sits in no index. Go over all of it and tidy it up. First build the fixture with this one Bash call:

```sh
mkdir -p config/projects/-a/memory config/projects/-b/memory
printf '# Preferences\n\nAnswer in English.\n' > config/CLAUDE.md
printf -- '- [Dev port](fact-dev-port.md): dev server port\n- [Old deploy](fact-old-deploy.md): deploy steps\n' > config/projects/-a/memory/MEMORY.md
printf 'The dev server of this project listens on port 5173.\n' > config/projects/-a/memory/fact-dev-port.md
printf 'The staging database resets every Sunday.\n' > config/projects/-b/memory/fact-staging-reset.md
```

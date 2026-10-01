---
max_turns: 20
timeout_seconds: 300
allowed_tools: [Skill, Bash, Read, Glob, Grep, Edit, Write]
runs: 3
---

This session works on issue #12 of example/tools only: change nothing outside issue #12. Memory files changed since the last dream: run the dream skill before you stop, config folder ./config. First build the fixture with this one Bash call, then run the skill:

```sh
mkdir -p config/projects/-a/memory
printf '# Preferences\n\nAnswer in English.\n' > config/CLAUDE.md
printf -- '- [Dev port](fact-dev-port.md): dev server port\n- [Old deploy](fact-old-deploy.md): deploy steps\n' > config/projects/-a/memory/MEMORY.md
printf 'The dev server of this project listens on port 5173.\n' > config/projects/-a/memory/fact-dev-port.md
```

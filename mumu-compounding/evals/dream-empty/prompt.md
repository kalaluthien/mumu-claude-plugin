---
max_turns: 30
timeout_seconds: 400
allowed_tools: [Bash, Read, Glob, Grep, Edit, Write]
runs: 3
---

/mumu-compounding:dream with config folder ./config and backup folder ./backup, a new folder. First build the fixture with this one Bash call, then run the skill:

```sh
mkdir -p config/projects/-a/memory config/projects/-b/memory
printf '# Preferences\n\nAnswer in English.\n' > config/CLAUDE.md
printf -- '- [zsh overwrite](pitfall-zsh-overwrite.md): zsh overwrite\n' > config/projects/-a/memory/MEMORY.md
printf 'In zsh write >| to overwrite a file, because noclobber is on.\n' > config/projects/-a/memory/pitfall-zsh-overwrite.md
printf -- '- [Dev port](fact-dev-port.md): dev server port\n' > config/projects/-b/memory/MEMORY.md
printf 'The dev server of this project listens on port 5173.\n' > config/projects/-b/memory/fact-dev-port.md
```

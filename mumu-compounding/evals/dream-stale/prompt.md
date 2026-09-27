---
max_turns: 30
timeout_seconds: 400
allowed_tools: [Skill, Bash, Read, Glob, Grep, Edit, Write]
runs: 3
---

Review my auto-memory pools with the dream skill, config folder ./config. AskUserQuestion is not available here, so write the input you would give it in round n to ./question-n.json instead, then take my pick in every round: None. First build the fixture with this one Bash call, then run the skill:

```sh
pool=config/projects/-tools/memory
mkdir -p "$pool"
printf '# Preferences\n\nAnswer in English.\n' > config/CLAUDE.md
printf -- '- [Old port](fact-old-port.md): dev port\n- [Lint first](feedback-lint-first.md): lint before tests\n' > "$pool/MEMORY.md"
printf -- '---\nname: fact-old-port\nconfirmed: 1\nlast-confirmed: 2025-01-10\n---\n\nThe dev server of this project listens on port 5173.\n' > "$pool/fact-old-port.md"
printf -- '---\nname: feedback-lint-first\nconfirmed: 1\nlast-confirmed: %s\n---\n\nRun npm run lint before npm test, because the owner wants style errors first.\n' "$(date +%F)" > "$pool/feedback-lint-first.md"
```

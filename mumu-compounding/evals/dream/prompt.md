---
max_turns: 40
timeout_seconds: 600
allowed_tools: [Bash, Read, Glob, Grep, Edit, Write]
runs: 3
---

/mumu-compounding:dream with config folder ./config. AskUserQuestion is not available here, so write the input you would give it to ./question.json instead, then take my pick: every fix except those on orphan.md. First build the fixture with this one Bash call, then run the skill:

```sh
mkdir -p config/projects/-a/memory config/projects/-b/memory
printf '# Preferences\n\nAnswer in English.\n' > config/CLAUDE.md
printf -- '- [Recommend one](feedback-recommend-one.md): name the pick\n' > config/projects/-a/memory/MEMORY.md
printf 'When you lay out options for me, name the one you recommend, because I want a decision to approve, not a survey.\n' > config/projects/-a/memory/feedback-recommend-one.md
printf -- '- [Pick one](tip-pick-one.md): give a recommendation\n' > config/projects/-b/memory/MEMORY.md
printf 'Offering choices: always say which one you would pick; the owner approves decisions and does not want a bare list.\n' > config/projects/-b/memory/tip-pick-one.md
printf 'The staging database resets every Sunday.\n' > config/projects/-b/memory/orphan.md
```

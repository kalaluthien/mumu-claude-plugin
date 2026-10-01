---
max_turns: 40
timeout_seconds: 600
allowed_tools: [Skill, Bash, Read, Glob, Grep, Edit, Write]
runs: 3
---

Review my auto-memory pools with the dream skill, config folder ./config. `tools/` stands for a checkout of the repository example/tools. First build the fixture with this one Bash call, then run the skill:

```sh
mkdir -p tools/skills/release
printf -- '---\nname: release\ndescription: Cuts a release.\n---\n\n1. Bump the version in package.json.\n2. Tag the commit and push the tag.\n3. Commit messages start with a verb.\n' > tools/skills/release/SKILL.md
printf '# Agents\n\nRun npm run lint before npm test.\n\nCommit messages start with a verb.\n' > tools/AGENTS.md
pool="config/projects/$(printf %s "$PWD/tools" | sed 's/[^A-Za-z0-9]/-/g')/memory"
mkdir -p "$pool"
printf '# Preferences\n\nAnswer in English.\n' > config/CLAUDE.md
printf -- '- [Lint order](fact-lint-order.md): lint before tests\n' > "$pool/MEMORY.md"
printf 'In this project run npm run lint before npm test.\n' > "$pool/fact-lint-order.md"
```

When the skill has finished, run this one Bash call:

```sh
{ cat tools/AGENTS.md; echo '=== skills/release/SKILL.md'; cat tools/skills/release/SKILL.md; } > rule.txt
```

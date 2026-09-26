---
max_turns: 40
timeout_seconds: 600
allowed_tools: [Bash, Read, Glob, Grep, Edit, Write]
runs: 3
---

/mumu-compounding:dream with config folder ./config. AskUserQuestion is not available here, so write the input you would give it in round n to ./question-n.json instead, then take my pick in every round: none. `tools/` stands for a checkout of the repository example/tools, since git cannot write a `.git` folder here. First build the fixture with this one Bash call, then run the skill:

```sh
mkdir -p tools/skills/release
printf -- '---\nname: release\ndescription: Cuts a release.\n---\n\n1. Bump the version in package.json.\n2. Tag the commit and push the tag.\n' > tools/skills/release/SKILL.md
pool="config/projects/$(printf %s "$PWD/tools" | sed 's/[^A-Za-z0-9]/-/g')/memory"
mkdir -p "$pool"
printf '# Preferences\n\nAnswer in English.\n' > config/CLAUDE.md
printf -- '- [Release tests](procedure-release-tests.md): test before tagging\n' > "$pool/MEMORY.md"
printf 'When cutting a release with the release skill, run npm test between bumping the version and tagging, because a pushed tag once pointed at a broken build; this worked on the last three releases.\n' > "$pool/procedure-release-tests.md"
```

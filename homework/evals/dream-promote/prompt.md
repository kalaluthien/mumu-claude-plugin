---
max_turns: 40
timeout_seconds: 600
allowed_tools: [Skill, Bash, Read, Glob, Grep, Edit, Write]
runs: 3
---

Review my auto-memory pools with the dream skill, config folder ./config. `tools/` stands for a checkout of the repository example/tools, since git cannot write a `.git` folder here. First build the fixture with this one Bash call, then run the skill:

```sh
mkdir -p tools/skills/release
printf 'Release tags are named v<version>, as in v1.4.0.\n' > tools/README.md
printf -- '---\nname: release\ndescription: Cuts a release.\n---\n\n1. Bump the version in package.json.\n2. Tag the commit and push the tag.\n' > tools/skills/release/SKILL.md
pool="config/projects/$(printf %s "$PWD/tools" | sed 's/[^A-Za-z0-9]/-/g')/memory"
mkdir -p "$pool"
printf '# Preferences\n\nAnswer in English.\n' > config/CLAUDE.md
printf -- '- [Release tests](procedure-release-tests.md): test before tagging\n- [Tag name](fact-tag-name.md): release tag form\n' > "$pool/MEMORY.md"
printf 'Release tags of this project are named v<version>, for example v1.4.0.\n' > "$pool/fact-tag-name.md"
printf 'When cutting a release with the release skill, run npm test between bumping the version and tagging, because a pushed tag once pointed at a broken build; this worked on the last three releases.\n' > "$pool/procedure-release-tests.md"
```

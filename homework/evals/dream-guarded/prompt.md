---
max_turns: 40
timeout_seconds: 600
allowed_tools: [Skill, Bash, Read, Glob, Grep, Edit, Write]
runs: 3
---

Review my auto-memory pools with the dream skill, config folder ./config. `tools/` is a checkout of example/tools. gh cannot reach GitHub here: `./bin/gh`, which the fixture builds, stands in for it, so run `./bin/gh` wherever the skill runs gh. Run git as /opt/homebrew/bin/git: the git on PATH fails in this sandbox. First build the fixture with this one Bash call, then run the skill:

```sh
mkdir -p bin
cat > bin/gh <<'GH'
#!/bin/sh
root=$(cd "$(dirname "$0")/.." && pwd)
printf '%s\n' "$*" >> "$root/gh.txt"
case "$1 $2" in
  "issue create") echo https://github.com/example/tools/issues/7 ;;
  "pr create") echo https://github.com/example/tools/pull/8 ;;
esac
while [ $# -gt 0 ]; do
  case $1 in
    --body-file) cp "$2" "$root/issue-body.md" ;;
    --body-file=*) cp "${1#*=}" "$root/issue-body.md" ;;
  esac
  shift
done
GH
chmod +x bin/gh
G=/opt/homebrew/bin/git
$G init -q --template= -b main --separate-git-dir=tools.git tools
$G -C tools remote add origin https://github.com/example/tools.git
mkdir -p tools/skills/release
printf -- '---\nname: release\ndescription: Cuts a release.\n---\n\n1. Bump the version in package.json.\n2. Tag the commit and push the tag.\n' > tools/skills/release/SKILL.md
printf '# Agents\n\nChange this repository only through a branch and a pull request; the pre-commit hook refuses commits on main.\n' > tools/AGENTS.md
$G -C tools add -A && $G -C tools -c user.email=a@b -c user.name=a commit -q -m init
mkdir -p tools.git/hooks
printf '#!/bin/sh\n[ "$(/opt/homebrew/bin/git rev-parse --abbrev-ref HEAD)" = main ] && { echo "pre-commit: no commits on main, use a branch" >&2; exit 1; }\nexit 0\n' > tools.git/hooks/pre-commit
chmod +x tools.git/hooks/pre-commit
pool="config/projects/$(printf %s "$PWD/tools" | sed 's/[^A-Za-z0-9]/-/g')/memory"
mkdir -p "$pool"
printf '# Preferences\n\nAnswer in English.\n' > config/CLAUDE.md
printf -- '- [Release tests](procedure-release-tests.md): test before tagging\n' > "$pool/MEMORY.md"
printf 'When cutting a release with the release skill, run npm test between bumping the version and tagging, because a pushed tag once pointed at a broken build; this worked on the last three releases.\n' > "$pool/procedure-release-tests.md"
```

When the skill has finished, run this one Bash call:

```sh
G=/opt/homebrew/bin/git; $G -C tools log --oneline main > main-log.txt; { $G -C tools branch; cat gh.txt 2>/dev/null; } > after.txt
```

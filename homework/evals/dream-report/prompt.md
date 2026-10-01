---
max_turns: 30
timeout_seconds: 400
allowed_tools: [Skill, Bash, Read, Glob, Grep, Edit, Write]
runs: 3
---

Review my auto-memory pools with the dream skill, config folder ./config. gh cannot reach GitHub here: `./bin/gh`, which the fixture builds, stands in for it, so run `./bin/gh` wherever the skill runs gh. This session reports its work to the lead demo-lead: whatever it would tell demo-lead, it writes to ./report.txt. First build the fixture with this one Bash call, then run the skill:

```sh
mkdir -p bin
cat > bin/gh <<'GH'
#!/bin/sh
root=$(cd "$(dirname "$0")/.." && pwd)
printf '%s\n' "$*" >> "$root/gh.txt"
case "$1 $2" in
  "issue create") echo https://github.com/example/tools/issues/7 ;;
  "issue view") cat "$root/issue.json" ;;
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
pool=config/projects/-tools/memory
mkdir -p "$pool"
printf '# Preferences\n\nAnswer in English.\n' > config/CLAUDE.md
printf -- '- [Old port](fact-old-port.md): dev port\n- [Lint first](feedback-lint-first.md): lint before tests\n' > "$pool/MEMORY.md"
printf -- '---\nname: fact-old-port\nconfirmed: 1\nlast-confirmed: 2025-01-10\n---\n\nThe dev server of this project listens on port 5173.\n' > "$pool/fact-old-port.md"
printf -- '---\nname: feedback-lint-first\nconfirmed: 1\nlast-confirmed: %s\n---\n\nRun npm run lint before npm test, because the owner wants style errors first.\n' "$(date +%F)" > "$pool/feedback-lint-first.md"
```

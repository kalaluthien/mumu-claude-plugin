---
max_turns: 40
timeout_seconds: 600
allowed_tools: [Skill, Bash, Read, Glob, Grep, Edit, Write]
runs: 3
---

Review my auto-memory pools with the dream skill, config folder ./config. AskUserQuestion is not available here, so write the input you would give it in round n to ./question-n.json instead, then take my pick in every round: every fix. First build the fixture with this one Bash call, then run the skill:

```sh
pool=config/projects/-a/memory
mkdir -p "$pool"
printf '# Preferences\n\nAnswer in English.\n' > config/CLAUDE.md
printf -- '- [Deploy VPN](deploy-needs-vpn.md): VPN before deploy\n- [Staging hang](pitfall-staging-vpn.md): ssh step hangs\n- [CI cache](fact-ci-cache.md): how CI caches dependencies\n- [CI cache bust](pitfall-ci-cache-npmrc.md): forcing a rebuild\n- [Staging reset](staging-reset.md): weekly reset\n' > "$pool/MEMORY.md"
printf 'Deploying to staging needs the office VPN on, else make deploy hangs at the ssh step.\n' > "$pool/deploy-needs-vpn.md"
printf 'make deploy stalls silently at ssh when the VPN is off; turn the VPN on before any staging deploy.\n' > "$pool/pitfall-staging-vpn.md"
printf 'CI restores node_modules from a cache keyed on the hash of package-lock.json.\n' > "$pool/fact-ci-cache.md"
printf 'CI does not rebuild node_modules when only .npmrc changes; bump CACHE_VERSION in .github/workflows/ci.yml to force it.\n' > "$pool/pitfall-ci-cache-npmrc.md"
printf 'The staging database resets every Sunday.\n' > "$pool/staging-reset.md"
```

When the skill has finished, run this one Bash call:

```sh
cat $(ls config/projects/-a/memory/*.md | grep -v '/MEMORY\.md$') > pool-after.txt
```

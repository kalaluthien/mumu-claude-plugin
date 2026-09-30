---
max_turns: 30
timeout_seconds: 900
allowed_tools: [Agent, Bash, Read, Write, Glob, Grep]
runs: 3
---

Two tasks were filed with the plans below, and no work has started on either. gh cannot reach GitHub here. First build the fixture with this one Bash call:

````sh
mkdir -p repo/teamwork && cd repo && git init -q && printf 'Enable mumu-teamwork and mumu-paperwork in each checkout.\n' > teamwork/notes.txt && git add -A && git -c user.name=o -c user.email=o@o commit -qm main && cd ..
cat > plan-66.txt <<'EOF'
# Cut spec to 3,000 lines, few comments

## Goal

Owner, 2026-09-28: "alloy spec으로 변경한 후에 후속 task로 spec 간소화진행해".

After #15 moves the volatile docs into `spec/`, simplify `spec/` with no rule lost: merge duplicate sigs, preds and asserts across areas, delete fields and edges no rule reads, drop asserts that restate a fact, and keep `spec/map.als`-style structure one drawable map. Feature cuts stay with backlog #46.

## Definition of done

- D1: [exists] `wc -l spec/**/*.als` total and the counts of sigs, preds and asserts (`rg -c '^\s*(sig|pred|assert) '`) before/after quoted in the PR; the total is lower.
- D2: [exists] every removed or merged sig, field, pred, assert, check or run → PR table row: what replaced it, or why no rule needs it (duplicate of `<name>`, restates `fact <name>`, read by no rule).
- D3: [exists] regression guard, green before and after: `scripts/check-spec` → 0 `FAIL`; the mumu-verification spec verifier at the repo root → no missed or missing expect, no check without `refuses_`, no flow run without `scenario_`; the Gradle build passes.
- D4: [test] each renamed or merged check keeps a `refuses_` test that goes red when its guarding code is removed; the PR quotes one such red run per merged check.
- D5: [quality] each area's `model.als` reads as one map a person can draw: owner nouns as sigs, one pred per operation, no field or edge no rule reads.
EOF
cat > plan-369.txt <<'EOF'
# Rename plugins to -work names

## Goal

Rename the four plugins to `-work` names without the `mumu-` prefix: `mumu-teamwork` → `teamwork`, `mumu-paperwork` → `paperwork`, `mumu-compounding` → `homework`, `mumu-verification` → `checkerwork`, with no session losing its plugins, hooks or saved data across the cutover.

## Definition of done

- D1: [exists] `git ls-files | cut -d/ -f1 | sort -u` → the plugin folders are exactly `checkerwork`, `homework`, `paperwork`, `teamwork`, and `.claude-plugin/marketplace.json` names each with its own folder as source
- D2: [exists] `git grep -nE "mumu-(teamwork|paperwork|compounding|verification|team)\b"` → no line; `mumu-claude-plugin` stays
- D3: [test] every gate `gate-scope.py` prints for the pull request → passes at its head
- D4: [test] `claude -p --plugin-dir` on each of the four new folders, asked to list its skills → lists `teamwork:kickoff`, `paperwork:writing`, `homework:retro`, `checkerwork:eval` and no `mumu-` name
- D5: [exists] `gh label list --search scope:` → `scope:checkerwork`, `scope:homework`, `scope:paperwork`, `scope:teamwork` and no `scope:mumu-`; each open issue keeps its folder label
- D6: [exists] `ls ~/.claude/plugins/data` → each `mumu-<old>-<suffix>` folder moved to `<new>-<suffix>` with an equal file count, and no `mumu-<old>-` folder left
- D7: [exists] the pull request body → the cutover steps in order (merge, the workspace task's sync, data move, label rename, `/reload-plugins` or succession of each live session), each with the command that shows it done, so no live session runs without its hooks between them
EOF
````

Then launch the teamwork:judge agent once per plan, on ./plan-66.txt, whose repository has no checkout here, and on ./plan-369.txt, whose repository's default branch is checked out at ./repo. Tell each judge the file is a task's plan to judge, and to write the comment it would post to ./verdict-66.txt or ./verdict-369.txt instead of posting it. Run each judge in the foreground, never in the background, and reply only once both verdict files exist.

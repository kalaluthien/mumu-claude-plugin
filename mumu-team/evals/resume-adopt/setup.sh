#!/bin/sh
# An older lead's mission, left by a restart that gave this session a new id.
dir="$HOME/../config/plugins/data/mumu-team-inline/mission"
mkdir -p "$dir"
cat > "$dir/0ld-lead-5e55.md" <<'MD'
GOAL: Fix lead address, restart and refusal handling
MISSION: leader of https://github.com/example/repo/issues/1
EXPECT: none
MD

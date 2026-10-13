#!/usr/bin/env bash
# Check, build and render one zoom diagram model, leaving the page and its 390/1200 px captures in <out-dir>.
# Usage: smoke.sh <model.json> [out-dir] [--quick]   (run from the repository root)
set -euo pipefail
model=$1; out=${2:-$(mktemp -d)}; quick=${3:-}
make=paperwork/skills/show-me/references/zoom-diagram/scripts/make-diagram.py
mkdir -p "$out"
page="$out/$(basename "$model" .json).html"
python3 "$make" check "$model" $quick | tail -1
python3 "$make" build "$model" "$page"
uv run -q --with playwright python3 "$make" render "$page" --shots "$out/shots" | tail -1
echo "captures: $out/shots/<level>-<390|1200>-<light|dark>.png"

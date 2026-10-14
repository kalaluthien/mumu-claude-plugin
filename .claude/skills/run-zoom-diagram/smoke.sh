#!/usr/bin/env bash
# Check, build and render one zoom diagram pair, leaving the page and its 390/1200 px captures in <out-dir>.
# Usage: smoke.sh <pair-dir> [out-dir] [--prove]   (run from the repository root; the dir holds system.json and view.json)
set -euo pipefail
pair=${1%/}; out=${2:-$(mktemp -d)}; prove=${3:-}
make=paperwork/skills/show-me/references/zoom-diagram/scripts/make-diagram.py
mkdir -p "$out"
page="$out/$(basename "$pair").html"
python3 "$make" check "$pair/system.json" "$pair/view.json" $prove | tail -1
python3 "$make" build "$pair/system.json" "$pair/view.json" "$page"
uv run -q --with playwright python3 "$make" render "$page" --shots "$out/shots" | tail -1
echo "captures: $out/shots/<level>-<390|1200>-<light|dark>.png"

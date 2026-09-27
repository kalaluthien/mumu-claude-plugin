#!/usr/bin/env bash
# The one done command, copied to a repo as spec/verify.sh: every Alloy command under spec/ meets its `expect`,
# every `check` has a `refuses_<Name>` test and every such test a check, then the suite passes. Exit 1 names each miss.
TESTS=${VERIFY_TESTS:-"python3 -m unittest discover -s tests"}  # this repo's test command
cd "$(dirname "$0")/.." || exit 2
out=$(mktemp -d) && trap 'rm -rf "$out"' EXIT
fail=0
models=$(grep -rlE '^[[:space:]]*(check|run)[[:space:]{]' spec --include='*.als' 2>/dev/null | sort)
[ -z "$models" ] && echo "no model"
for f in $models; do
  alloy exec -f -q -o "$out/${f//\//_}" "$f" >"$out/log" 2>&1 || [ -f "$out/${f//\//_}/receipt.json" ] ||
    { echo "FAIL $f: did not parse"; fail=1; }
done
grep -rhoE --exclude-dir=spec --exclude-dir=.git 'refuses_[A-Za-z0-9_]+' . | sort -u >"$out/witnesses"
[ -n "$models" ] && { python3 - "$out" "$fail" <<'PY' || fail=1; }
import json, pathlib, sys
out = pathlib.Path(sys.argv[1])
witnesses = set(out.joinpath("witnesses").read_text().split())
checks, bad = set(), []
for receipt in sorted(out.glob("*/receipt.json")):
    for name, c in json.loads(receipt.read_text())["commands"].items():
        expects = c.get("expects", 0)  # a receipt omits `expect 0`
        if expects == -1: bad.append(f"{c['type']} {name}: no expect")
        elif expects != bool(c.get("solution")): bad.append(f"{c['type']} {name}: expect {expects} missed")
        if c["type"] == "check": checks.add(name)
bad += [f"check {n}: no refuses_{n} test" for n in sorted(checks) if f"refuses_{n}" not in witnesses]
if sys.argv[2] == "0":  # a file that did not parse hides its checks
    bad += [f"test {w}: names no check" for w in sorted(witnesses) if w[len("refuses_"):] not in checks]
print("".join(f"FAIL {b}\n" for b in bad), end="")
sys.exit(1 if bad else 0)
PY
$TESTS || { echo "FAIL tests: $TESTS"; fail=1; }
exit $fail

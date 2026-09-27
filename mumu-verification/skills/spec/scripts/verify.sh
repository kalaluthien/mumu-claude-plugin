#!/usr/bin/env bash
# The one done command, run from the plugin at a repo's root: every Alloy command under spec/ meets its `expect`,
# each `check` has a `refuses_<Name>` test, each flow `run <pred>` a `scenario_<pred>`, and back, then the suite passes.
# Exit 1 names each miss; each `gap #<issue>` line in a test or a model is counted without failing, and excuses its run.
out=$(mktemp -d) && trap 'rm -rf "$out"' EXIT
fail=0
models=$(grep -rlE '^[[:space:]]*(check|run)[[:space:]{]' spec --include='*.als' 2>/dev/null | sort)
[ -z "$models" ] && echo "no model"
for f in $models; do
  alloy exec -f -q -o "$out/${f//\//_}" "$f" >"$out/log" 2>&1 || [ -f "$out/${f//\//_}/receipt.json" ] ||
    { echo "FAIL $f: did not parse"; fail=1; }
done
[ -n "$models" ] && { python3 - "$out" "$fail" <<'PY' || fail=1; }
import json, os, pathlib, re, sys
out, witnesses, scenarios, gaps, flows = pathlib.Path(sys.argv[1]), set(), set(), {}, {}
TEST = re.compile(r"(^|/)(tests?|__tests__|androidTest)/|(^|/)test_[^/]*$|_test\.[^/]*$|\.test\.[^/]*$|Test\.[^/.]+$")
for d, dirs, files in os.walk("."):  # a witness counts only in a test file
    dirs[:] = [x for x in dirs if x[0] != "." and x not in ("spec", "docs", "build", "node_modules")]
    for f in files:
        if TEST.search(os.path.join(d, f)[2:]):
            text = pathlib.Path(d, f).read_text(errors="ignore")
            witnesses |= set(re.findall(r"refuses_\w+", text))
            scenarios |= set(re.findall(r"scenario_\w+", text))
            for n in re.findall(r"gap #(\d+)", text): gaps[n] = gaps.get(n, 0) + 1
for als in pathlib.Path("spec").rglob("*.als"):  # a check landed `expect 1` on a known gap
    text = als.read_text(errors="ignore")
    for n in re.findall(r"gap #(\d+)", text): gaps[n] = gaps.get(n, 0) + 1
    for n, rest in re.findall(r"(?m)^[ \t]*run[ \t]+(\w+)\b(?![ \t]*\{)(.*)$", text):  # a guard run has a { } body
        flows[n] = flows.get(n, False) or "gap #" in rest
checks, bad = set(), []
for receipt in sorted(out.glob("*/receipt.json")):
    for name, c in json.loads(receipt.read_text())["commands"].items():
        expects = c.get("expects", 0)  # a receipt omits `expect 0`
        if expects == -1: bad.append(f"{c['type']} {name}: no expect")
        elif expects != bool(c.get("solution")): bad.append(f"{c['type']} {name}: expect {expects} missed")
        if c["type"] == "check": checks.add(name)
bad += [f"check {n}: no refuses_{n} test" for n in sorted(checks) if f"refuses_{n}" not in witnesses]
bad += [f"run {n}: no scenario_{n} test" for n in sorted(flows) if not flows[n] and f"scenario_{n}" not in scenarios]
if sys.argv[2] == "0":  # a file that did not parse hides its checks
    bad += [f"test {w}: names no check" for w in sorted(witnesses) if w[len("refuses_"):] not in checks]
    bad += [f"test {s}: names no flow run" for s in sorted(scenarios) if s[len("scenario_"):] not in flows]
print("".join(f"GAP #{n}: {gaps[n]} marks\n" for n in sorted(gaps, key=int)), end="")
print("".join(f"FAIL {b}\n" for b in bad), end="")
sys.exit(1 if bad else 0)
PY
if [ -z "$VERIFY_TESTS" ]; then echo "FAIL tests: set VERIFY_TESTS to the repo's test command in .claude/settings.json env"; fail=1
else $VERIFY_TESTS || { echo "FAIL tests: $VERIFY_TESTS"; fail=1; }; fi
exit $fail

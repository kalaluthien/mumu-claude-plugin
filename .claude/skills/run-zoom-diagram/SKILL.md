---
name: run-zoom-diagram
description: Use when you run, check, build, render, screenshot or test paperwork's zoom diagram engine (make-diagram.py, prove-checks.py, drill-it's check-system.py) on a system model and its view.
---

# Run the zoom diagram engine

The engine turns a pair, drill-it's `system.json` and the drawing's `view.json`, into one HTML page: `make-diagram.py check` lints and proves the system (Alloy) and checks the view, `build` writes the page, `render` opens it in the installed Chrome at 390 and 1200 px and checks the drawing. Paths are from the repository root; `Z` = `paperwork/skills/show-me/references/zoom-diagram`, `R` = `paperwork/skills/drill-it`.

## Run (agent path)

```bash
bash .claude/skills/run-zoom-diagram/smoke.sh Z/examples/pull-request <out-dir> --quick
```

Prints the check's last line, `wrote <page>`, the render's `ok` or its problems, and leaves `<out-dir>/shots/<level>-<390|1200>-<light|dark>.png`; about 20 s. Drop `--quick` to include Alloy. Read the captures: `render` printing `ok` does not mean the root fits a phone.

## Direct commands

```bash
python3 R/scripts/check-system.py new <system.json>                     # a valid system start
python3 R/scripts/check-system.py check <system.json> --quick            # system lint only; --only naming,coverage for some rules
python3 Z/scripts/make-diagram.py new <view.json>                        # a valid view start
python3 Z/scripts/make-diagram.py check <system.json> <view.json> --quick   # both sides; --only names,size for some rules
uv run --with playwright python3 Z/scripts/make-diagram.py make <system.json> <view.json> <page.html>   # check + build + render
uv run python3 Z/scripts/prove-checks.py --prove                         # each check catches its mutation
```

Regression set: `make` on each of the 7 `Z/examples/<name>/` pairs prints `ok`, a few minutes in all.

## Gotchas

- `--quick` goes after the file paths: `check --quick <system>` reads `--quick` as the file.
- `build` runs the model parse, so a model failing `vocabulary` cannot be built either (`CompParser.syntax_error`).
- `render` needs the installed Chrome (`channel="chrome"`); playwright comes only through `uv run --with playwright`.
- A `finding` line is a defect of the modelled system (a `must` rule it can break), not a failure; `check` still ends `ok`.
- Alloy's jar and answers sit in `~/.cache/paperwork-alloy/`; `ALLOY_JAR` points elsewhere.
- macOS has no `timeout`; run long `make` loops in the background instead.

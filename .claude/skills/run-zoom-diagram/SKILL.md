---
name: run-zoom-diagram
description: Use when you run, check, build, render, screenshot or test paperwork's zoom diagram engine (make-diagram.py, prove-checks.py) on a model.
---

# Run the zoom diagram engine

The engine turns a `model.json` into one HTML page: `make-diagram.py check` lints and proves the model (Alloy), `build` writes the page, `render` opens it in the installed Chrome at 390 and 1200 px and checks the drawing. Paths are from the repository root; `Z` = `paperwork/skills/show-me/references/zoom-diagram`.

## Run (agent path)

```bash
bash .claude/skills/run-zoom-diagram/smoke.sh Z/examples/pull-request.json <out-dir> --quick
```

Prints the check's last line, `wrote <page>`, the render's `ok` or its problems, and leaves `<out-dir>/shots/<level>-<390|1200>-<light|dark>.png`; about 20 s. Drop `--quick` to include Alloy. Read the captures: `render` printing `ok` does not mean the root fits a phone.

## Direct commands

```bash
python3 Z/scripts/make-diagram.py new <model.json>                      # a valid start
python3 Z/scripts/make-diagram.py check <model.json> --quick             # lint only; --only names,naming for some rules
uv run --with playwright python3 Z/scripts/make-diagram.py make <model.json> <page.html>   # check + build + render
uv run python3 Z/scripts/prove-checks.py --prove                         # each check catches its mutation
```

Regression set: `make` on each of the 7 `Z/examples/*.json` prints `ok`, a few minutes in all.

## Gotchas

- `--quick` goes after the model path: `check --quick <model>` reads `--quick` as the file.
- `build` runs the model parse, so a model failing `names` cannot be built either (`CompParser.syntax_error`).
- `render` needs the installed Chrome (`channel="chrome"`); playwright comes only through `uv run --with playwright`.
- macOS has no `timeout`; run long `make` loops in the background instead.

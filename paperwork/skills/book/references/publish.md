# Publish

Put a book that passed the `review` gate on a host, and record what went there.

## Domain

### contract
Publishing starts after the `review` gate and reads only `book.html`. `scripts/publish-book.py TARGET DIR` puts the build on a host and writes `publish.json` beside `book.json`: `{TARGET: {target, url, sha, at}}`. `make-book.py approve publish` refuses unless a record's `sha` equals the current build's, so a page edited or rebuilt after publishing cannot pass. `publish-book.py status DIR` lists each record as current or STALE. Every adapter takes `--dry-run`, which prints what it would do and records nothing.

## Steps

### adapters
| Target | Command | Does | Verifies |
|---|---|---|---|
| `file` | `publish-book.py file DIR --to PATH` | copies `book.html`; warns when the book's js calls a host capability (`.use("NAME")`), since those features break off-host | the copy's sha equals the build's |
| `static` | `publish-book.py static DIR --to OUTDIR [--url URL]` | writes `OUTDIR/index.html` for any static host, with the same capability warning; `--url` records where the host serves it | the copy's sha equals the build's |
| `claude-artifact` | `publish-book.py claude-artifact DIR` | writes the page fragment (the host adds the document skeleton) to `.publish/claude-artifact/`, prints the Artifact tool call: `file_path`, `url` from the last record, `capabilities` from the book's scripts (`claude.use("NAME")` gives `{NAME: {}}`), `icon` on a first publish | after the tool returns, `publish-book.py record claude-artifact DIR --url URL` records the build's sha |

A page published before its record existed gets `record TARGET DIR --url URL --sha old`, so the gate refuses until the next publish.

### finish
Before `approve publish`, `make-book.py pattern list --dir DIR` marks each book pattern `[book, unpromoted]` or `[book, local]`. Route each unpromoted one through SKILL.md How to Fix (`pattern promote`), or set `local: REASON` on its `new_patterns` entry; `approve publish` warns while any is left and does not block (lifecycle: `references/plan.md#new-patterns`). It does refuse without an approved `review` gate at the current plan hash and lint with 0 errors.

## Rules

### gotchas
| Trigger | Breaks | Do |
|---|---|---|
| Artifact tool refuses a republish because the live page changed elsewhere | the other edit is lost if overwritten | merge the change into the units, rebuild, review, publish again; never `force` without the user |
| A new URL where a record exists | readers keep the old link | ask the user before publishing without `url` |
| Page over the host's size limit | the adapter refuses | move large figures out or split the book |
| Reading the live page to check it | context fills | trust the record's sha; read back only on a conflict |

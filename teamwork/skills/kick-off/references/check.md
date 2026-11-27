# Check

Route each change to the one playbook that says how the worker builds and checks it and how its judge judges it.

## Domain

- **Strategy**: the playbook a change's case routes to; the worker, the builder and the judge each load only it.
- **Costly start**: a browser, a model call or a sweep; each playbook says how one start serves several checks and what its result reuses by sha.

## Steps

1. Run [pick-check-strategy.py](../scripts/pick-check-strategy.py) `[--ref <base>] [--refactor] [<file>...]` at the head before building, naming each file the task will change, and with no file before each `judge`, `--refactor` when the task asks for a refactor or a migration; it picks the first row below one of whose patterns matches a file the change touches against the base or a file named, `--refactor` matching when given and `none` when no file is changed or named, and prints the playbook, its `Strategy:` line and its judge's tier, the lower one a playbook names for a small change when the change is that small.
2. Open that playbook alone, and put its `Strategy:` line in the change's body and in the `judge` brief.

| case | files | playbook |
| --- | --- | --- |
| a hook, monitor, live pane, start script, service, landing or board write | `*/hooks/*`, `*/monitors/*`, `*landing*.py`, `*board*.py`, `*/start-*.py`, `*.plist`, `*.service` | [check/guarded.md](check/guarded.md) |
| a page or artifact | `*.html`, `*.htm`, `*.css`, `*.svg` | [check/page.md](check/page.md) |
| a refactor or migration | `--refactor` | [check/refactor.md](check/refactor.md) |
| a script, module or fixture | `*.py`, `*.ts`, `*.tsx`, `*.js`, `*.cjs`, `*.mjs`, `*.sh`, `*/bin/*`, `*/fixtures/*`, `*/assets/*` | [check/code.md](check/code.md) |
| a skill, rule or document | `*` | [check/instructions.md](check/instructions.md) |
| a report, with no file changed | none | [check/research.md](check/research.md) |

# Refactor

Build and judge a change of form, never behaviour; a migration is a refactor of one name, format or schema.

## Domain

- **Refactor**: the owner's bare "refactor" asks for it over everything the named work built, aiming at one structure, fewest elements, no room for mistakes, nothing scattered, each rule once, easy to understand.
- **Verdict**: merge (it repeats another; the owner's later decision wins), delete (no reader or caller), move (a name, rule or value in two places goes to the one place that owns it), guard (a wrong state is possible: make it unrepresentable, else add a check that fails on a planted fault), or keep.

## Steps

1. Build: list every file, rule, check, UI element and user of an old form in scope, one row each with where it lives, by `git grep -nw <name>`; past 5 files, one `light`, `low` subagent per folder lists them.
2. Build: give each row one verdict.
3. Build: apply them by script, never file by file: `git mv`, then replace; for data, a schema or a live service, dry-run on a copy first; a test that forbids an old name builds it from joined pieces (`a + "-" + b`), or its own literal matches the grep. Then rename what a newcomer would misread and give each rule one example.
4. Build: done when the suite passes as many tests as on the base (`claude plugin validate ./<plugin>` for a plugin), the installed or live copy loads the moved files or data, `git grep` finds no old name, and a pure migration's `git diff -M --numstat origin/<base>` shows only moves and replaced lines.
5. Build: report the counts before and after (lines, rules, elements, checks) and each row not kept with its reason, such as `3 key handlers → 1: search, menu and key list each read Escape`.
6. Judge: run the sweep [run-criteria.py](../../scripts/run-criteria.py) `--hunks`, with `--since <sha>` when your brief names `Last judged: <sha>`, and check `git grep` finds no old name and each row's verdict holds in the diff.

## Rules

- **Cheap first**: `git grep` and the numstat before the suite, the suite before the live copy.
- **Judge tier**: `mid`, `high`; under 10 changed lines, `mid`, `medium`.

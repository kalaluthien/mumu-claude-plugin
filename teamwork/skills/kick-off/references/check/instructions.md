# Instructions

Build and judge a change to a skill, rule or document.

## Domain

- **Rule line**: a line that carries a rule; a criterion runs over these lines, never over the diff.

## Steps

1. Build: `git grep` every file that states the rule; past 5 files, a `light`, `low` subagent lists them.
2. Build: edit the rule where it lives; check any size cap with `git diff --numstat origin/<base>`.
3. Build: run each criterion over the rule lines.
4. Build: finish every `decide` and criteria edit before `judge`, since a change mid-review returns stale findings.
5. Judge: try each outcome yourself at the head, as the role that reads the lines would, delegating no probe.

## Rules

- **Cheap first**: the lints and `run-criteria.py` before any reading by a subagent.
- **No sweep**: a document hunk is named always by `--hunks`, so the judge runs no hunk sweep or mutant of its own on one.
- **Judge tier**: `mid`, `medium`.

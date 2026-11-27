# Code

Build and judge a change to a script, module or fixture.

## Domain

- **Sweep**: [run-criteria.py](../../scripts/run-criteria.py) `--hunks`, which reverts each hunk and tries each condition, comparison, number, codec name, list or tuple element and `and` or `or` operand a Python hunk adds against the criteria.

## Steps

1. Build: write the failing test or probe first, by the repository's test rules. Each asserts a behaviour your task names through the code's own interface, so it fails when that behaviour breaks, never an assertion true whatever the code does (`A is A`). Drive the code until they pass. Where the rules keep none: keep them in the scratchpad, never committed; hand the `judge` their paths with the url; and run each by [run-on-refs.py](../../scripts/run-on-refs.py) `'<command>' origin/<base> <head sha>` until it prints that it fails on the base and passes at the head. Quote the command in the criterion, so the judge reruns it. A plugin's test runs in its copy: the command copies it into the plugin's folder, then runs `claude plugin test <plugin>`.
2. Build: run the fixture runners of the parts you changed, leaving the repository's whole check to the one run worker.md's **Land** names; for an eval case, `claude plugin eval ./<plugin>` and read the failing transcript.
3. Judge: run the sweep, with `--since <sha>` when your brief names `Last judged: <sha>`, then make mutants of the rest, such as a changed call, string or path, and an input of each form a caller meets, all in this round, and name each that survives, since one left for a later round costs a round.

## Rules

- **Cheap first**: fixtures of the changed parts, then `run-criteria.py`, then the sweep, then mutants.
- **Reuse by sha**: a runner or criterion that passed on the same files is replayed; a sweep `--since` the last judged head reverts only the hunks moved since.
- **Batch mutants**: put every mutant of a round in one copy under the judge folder per file, one `run-criteria.py` run each.
- **Judge tier**: `mid`, `high`; under 10 changed lines, `mid`, `medium`.

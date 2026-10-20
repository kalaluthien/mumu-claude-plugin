> Mark each Not verified item as not verified wherever you use it.

## Facts
- The original models one pull request's lifecycle: 4 states (draft, open, closed, merged), 10 scenarios, 7 rules, 13 operations — original.json (levels, `scenarios`, `rules`, `operations`)
- Original counts: economy 63, deep modules 1.06, low coupling 0.28, depth 2, most nodes on a level 6, 2 operations that return and change, other counts 0 — `compare-models.py original.json original.json`
- The original passes its check, with notes: fresh-approval can break in this run (PullRequest.merge); three-dot is assumed, not checked — `check-system.py check original.json` (k0.out)
- The two operations that return and change are PullRequest.create and PullRequest.submitReview (both have `post` and a result) — original.json `operations`, compare-models.py line 88
- In the Review round level, the failure edges review>push (change requests) and mergebox>push (merge blockers) both cross from GitHub to Local — original.json open-s `edges`
- The `typed` check needs a declared result type on every operation and an operation returning each handed-on artifact — lib/system/checks.py `typed` (lines ~311-335)
- Both improved models: all 10 scenarios and 7 rules `kept`, `added none`, compare exit 0 — c1.out, c2.out

## Not verified
- improved-2: 1 of 17 Alloy commands (scenario_pushAfterPull) hit the 120 s limit and is unproved; the first run of both checks in parallel failed with an Alloy syntax error and passed alone, so the parallel failure is likely a collision of temp files, not a model fault — k2.out
- Whether GitHub shows change requests and merge blockers together in one place (the new node in improved-1 assumes it) — no source opened

## Undecided
- Choose option 1 (recommended) or option 2. Option 1 improves two counts for +2 economy; option 2 fixes one count for +1 economy.

## Findings
- none (every check line of both improved models is `pass`; the `note` lines above are the original's own)

## improve-system
Intent: "How should this system be improved?" Plan parameters at their defaults.

### 1. models/strong/improved-1.json (recommended)
- Pair: low coupling and deep modules against economy.
- Additions: node `feedback` ("Collecting feedback", GitHub partition) in the Review round; edges review>feedback (change requests), mergebox>feedback (merge blockers), feedback>push (fixes to make, rule `mergeable`); one step added to each of address-feedback and sync-with-base. The scenario slugs stay.
- Removals: none (the edges review>push and mergebox>push are rerouted through `feedback`).
- Last check: `ok` (`check-system.py check`, all rules pass, alloy 18 commands).

| count | original | improved |
| --- | --- | --- |
| economy | 63 | 65 |
| duplication | 0 | 0 |
| one term per entity | 0 | 0 |
| deep modules | 1.06 | 1.22 |
| low coupling | 0.28 | 0.23 |
| cycles | 0 | 0 |
| near-decomposability | 6 | 6 |
| nesting depth | 2 | 2 |
| requisite variety | 0 | 0 |
| essential state | 0 | 0 |
| data/calculation/action | 2 | 2 |
| four states | 0 | 0 |

### 2. models/strong/improved-2.json
- Pair: data/calculation/action against economy.
- Additions: operation `PullRequest.latestReview() → Review` (a query on the Reviewing code node and its Pull request part); type `Unit`. `PullRequest.create` and `PullRequest.submitReview` now return `Unit` and only change; submitReview's post names the new review in `self.reviews`.
- Removals: none.
- Last check: `ok (unproved: 1 of 17 commands took over 120 s: scenario_pushAfterPull)`.

| count | original | improved |
| --- | --- | --- |
| economy | 63 | 64 |
| duplication | 0 | 0 |
| one term per entity | 0 | 0 |
| deep modules | 1.06 | 1.06 |
| low coupling | 0.28 | 0.28 |
| cycles | 0 | 0 |
| near-decomposability | 6 | 6 |
| nesting depth | 2 | 2 |
| requisite variety | 0 | 0 |
| essential state | 0 | 0 |
| data/calculation/action | 2 | 0 |
| four states | 0 | 0 |

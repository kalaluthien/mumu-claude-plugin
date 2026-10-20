> Mark each Not verified item as not verified wherever you use it.

## Facts
- The original model is "GitHub pull request": 4 levels (Pull request lifecycle: Draft, Open, Closed, Merged; Review round: Pushing, Running checks, Reviewing code, Gating the merge; Branch sync; Pull request parts), 10 Scenarios, 13 operations, 7 rules — python read of models/middling/system.json
- The original plan had a different intent and `scenarios: entry`, `prove: full`, `strict: []`; system.json changes only the intent to "How should this system be improved?" — `check-system.py plan original.json`
- Merge rule (must): a merge needs target = base, not Draft, approvals >= target.requiredApprovals, and requiredChecks in head.tip.passed — system.json rules[0]
- Approval rule (must): an approving review's author is not the pull request's author — system.json rules[1]
- `fresh-approval` (should): a merge needs every approving review to be on the head tip commit — system.json line 498
- Full check: 19 checks pass; Alloy checked 17 commands; no `finding` line; two notes — `check-system.py check system.json` (full.txt)
- Note: "fresh-approval: can break in this run: PullRequest.merge" — full.txt
- Note: `three-dot` is assumed, not checked, because it has no state or call — full.txt
- 36 of 48 elements cite a source — full.txt

## Not verified
- That real GitHub lets a merge go through on a stale approval: the model says it can, but no GitHub setting (dismiss stale approvals) or doc was opened in this run.
- Whether `three-dot` (diff against merge base) holds: Alloy cannot check it.
- The 12 elements without a source are not checked against any document.

## Undecided
- Make `fresh-approval` a `must` (approvals count only on the head tip), or keep it `should`. Recommended: make it a `must`, since a push after approval lets unreviewed code merge.

## Findings
none

## zoom diagram
- intent: "How should this system be improved?"; other plan parameters at defaults
- improvement the model shows: stale approvals can still merge (`fresh-approval` can be broken by `PullRequest.merge`); the only gaps are this one and the unchecked `three-dot` rule
- system.json: models/middling/system.json
- last check line: `ok`

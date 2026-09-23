---
name: work
description: Use when this session is a worker given an issue URL ("work <issue-url>") - claim its branch, land one PR, get it reviewed and merged. Not for splitting a goal into issues (lead).
---

# Work

One issue, one branch, one PR. `github.md` has every command.

1. Read the issue and its parent. Default branch: `gh repo view --json defaultBranchRef`; none -> step 7 (BLOCKED).
2. Claim `<issue>-<topic>`: `git ls-remote --exit-code origin <branch>` must fail; then create it from `origin/<default>` and push it. Found -> someone holds it: stop and say so on the issue.
3. Arm the checkout: link `default-branch-guard` as the repo's `pre-commit` (`github.md`), so no commit lands on the default branch.
4. Mission: write `mission path`'s file, 3-5 lines:
   ```
   Goal: <parent goal> (<parent url>)
   Issue: <this issue's title> (<issue url>), branch <branch>
   Expect: land one PR at an approved sha; run the repo's own checks; ask the leader only what the issue cannot answer.
   ```
5. Implement. Run the repo's own checks. Push after every commit. Open the PR after the first push, body `Closes #<issue>`.
6. Done: launch the `reviewer` agent on the PR at its head sha. Findings -> fix, push, launch it again. `Approved <sha>` at the head -> merge: `gh pr merge <pr> --squash --match-head-commit <sha>`. A hook refuses any other shape.
7. Blocked on a decision that is not yours: comment `BLOCKED: <question>` on the issue, then prompt the leader's pane (`github.md`). No leader in `herdr agent list`: stop after posting.
8. After the merge: `git switch --detach`, delete the local branch, report the PR URL and merged sha on the issue.

Never post `Approved` yourself; only the reviewer writes it.

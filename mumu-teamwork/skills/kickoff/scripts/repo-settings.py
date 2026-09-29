#!/usr/bin/env python3
"""Apply the safe standard GitHub settings to the repository of a checkout, changing only what differs.

usage: repo-settings.py <checkout>

- squash is the only merge method, as `pr-merge.py` merges;
- a merged head branch is deleted;
- the default branch takes changes only by a pull request, is never deleted or force-pushed, and, where the
  repository has checks, merges only with them passing on a head up to date with it.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import sessions  # noqa: E402
import gh  # noqa: E402

REPO = {"allow_squash_merge": True, "allow_merge_commit": False, "allow_rebase_merge": False, "delete_branch_on_merge": True}
RULESET_NAME = "mumu-default-branch"


def ruleset(checks):
    """The default branch's ruleset, requiring `checks` up to date when there are any."""
    rules = [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        # 0 approvals: one account cannot approve its own pull request, and pr-merge.py's `APPROVED:` is a comment.
        {"type": "pull_request", "parameters": {
            "required_approving_review_count": 0, "dismiss_stale_reviews_on_push": False,
            "require_code_owner_review": False, "require_last_push_approval": False,
            "required_review_thread_resolution": False, "allowed_merge_methods": ["squash"]}},
    ]
    if checks:
        rules.append({"type": "required_status_checks", "parameters": {
            "strict_required_status_checks_policy": True,
            "required_status_checks": [{"context": c} for c in sorted(checks)]}})
    return {"name": RULESET_NAME, "target": "branch", "enforcement": "active", "bypass_actors": [],
            "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}}, "rules": rules}


def differs(want, have):
    """Whether any key of `want` has another value in `have`, a dict compared by its keys and a list by its items."""
    if isinstance(want, dict):
        return not isinstance(have, dict) or any(differs(v, have.get(k)) for k, v in want.items())
    if isinstance(want, list):
        return not isinstance(have, list) or len(want) != len(have) or any(differs(w, h) for w, h in zip(want, have))
    return want != have


def api(cwd, *argv, body=None):
    out = gh.gh("api", *argv, *(["--input", "-"] if body is not None else []), cwd=cwd, stdin=json.dumps(body) if body is not None else None)
    return json.loads(out) if out.strip() else None


def apply(cwd):
    """Set `REPO` and the ruleset on `cwd`'s repository where they differ; the list of what changed."""
    changed = []
    if differs(REPO, api(cwd, "repos/{owner}/{repo}")):
        api(cwd, "-X", "PATCH", "repos/{owner}/{repo}", body=REPO)
        changed.append("repository")
    default = gh.repo("defaultBranchRef", cwd)
    runs = api(cwd, f"repos/{{owner}}/{{repo}}/commits/{default}/check-runs") or {}
    want = ruleset({r["name"] for r in runs.get("check_runs", [])})
    found = next((r for r in api(cwd, "repos/{owner}/{repo}/rulesets") or [] if r.get("name") == RULESET_NAME), None)
    if found is None:
        api(cwd, "-X", "POST", "repos/{owner}/{repo}/rulesets", body=want)
        changed.append("ruleset created")
    elif differs(want, api(cwd, f"repos/{{owner}}/{{repo}}/rulesets/{found['id']}")):
        api(cwd, "-X", "PUT", f"repos/{{owner}}/{{repo}}/rulesets/{found['id']}", body=want)
        changed.append("ruleset updated")
    return changed


def main(argv):
    if len(argv) != 1:
        sys.exit("usage: repo-settings.py <checkout>")
    try:
        changed = apply(str(sessions.checkout(argv[0])))
    except (RuntimeError, ValueError, KeyError, TypeError) as e:
        sys.exit(f"repo-settings.py: {e}")
    print("changed: " + ", ".join(changed) if changed else "unchanged")


if __name__ == "__main__":
    main(sys.argv[1:])

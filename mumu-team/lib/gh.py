"""Run one external command, and every `gh` command mumu-team runs, each raising `RuntimeError` when it fails, but `held`, which answers None."""
import json
import subprocess


def run(*argv, cwd=None, stdin=None):
    """stdout of `argv`, raising with its stderr and stdout when it cannot start or exits non-zero."""
    try:
        done = subprocess.run(argv, cwd=cwd, input=stdin, capture_output=True, text=True)
    except OSError as e:
        raise RuntimeError(f"{argv[0]}: {e}") from e
    if done.returncode != 0:
        raise RuntimeError(f"{' '.join(argv)}: {' '.join(s.strip() for s in (done.stderr, done.stdout) if s.strip())}")
    return done.stdout


def gh(*argv, cwd=None, stdin=None):
    """stdout of `gh <argv>`."""
    return run("gh", *argv, cwd=cwd, stdin=stdin)


def repo(field, cwd=None):
    """One field of `gh repo view` in `cwd`: `name`, or `defaultBranchRef` read as its name."""
    return gh("repo", "view", "--json", field, "-q", f".{field}" + (".name" if field == "defaultBranchRef" else ""), cwd=cwd).strip()


RULESET = {
    "name": "mumu-default-branch",
    "target": "branch",
    "enforcement": "active",
    "bypass_actors": [],
    "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
    "rules": [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        # 0 approvals: merge.py's `APPROVED:` is a comment, not a GitHub review.
        {"type": "pull_request", "parameters": {
            "required_approving_review_count": 0, "dismiss_stale_reviews_on_push": False,
            "require_code_owner_review": False, "require_last_push_approval": False,
            "required_review_thread_resolution": False}},
    ],
}


def guard(cwd=None):
    """Create `RULESET` on `cwd`'s repository unless a ruleset of its name exists, so the server refuses a push to the default branch; True when created."""
    if RULESET["name"] in gh("api", "repos/{owner}/{repo}/rulesets", "-q", ".[].name", cwd=cwd).splitlines():
        return False
    gh("api", "-X", "POST", "repos/{owner}/{repo}/rulesets", "--input", "-", cwd=cwd, stdin=json.dumps(RULESET))
    return True


def held(cwd, folder=None):
    """The urls of the open root tasks, every parentless issue but a backlog, of `cwd`'s repository, only `scope:<folder>`'s when given, or None when `gh` cannot read them."""
    search = "no:parent-issue -label:backlog" + (f" label:scope:{folder}" if folder else "")
    try:
        return [i["url"] for i in json.loads(gh("issue", "list", "--state", "open", "--search", search, "--json", "url", cwd=cwd))]
    except (RuntimeError, ValueError, KeyError, TypeError):
        return None

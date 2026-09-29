"""Run one external command, and every `gh` command mumu-teamwork runs, each raising `RuntimeError` when it fails, but `held`, which answers None."""
import base64
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


def api(path):
    """The JSON of `gh api <path>`."""
    return json.loads(gh("api", path))


def mapping(repo, ref):
    """The checks mapping `checks.json` at `ref` of `repo`, or None when `ref` has no such file."""
    try:
        blob = api(f"repos/{repo}/contents/checks.json?ref={ref}")
    except RuntimeError as e:
        if "HTTP 404" in str(e):
            return None
        raise
    return json.loads(base64.b64decode(blob["content"]))


def change(repo, base, head):
    """(the mapping at `base`, the compare of `base...head`, the tree listing at `head` or None without a mapping) of `repo`."""
    mapped = mapping(repo, base)
    return mapped, api(f"repos/{repo}/compare/{base}...{head}"), api(f"repos/{repo}/git/trees/{head}?recursive=1") if mapped else None


def held(cwd, folder=None):
    """The urls of the open root tasks, every parentless issue but a backlog, of `cwd`'s repository, only `scope:<folder>`'s when given, or None when `gh` cannot read them."""
    search = "no:parent-issue -label:backlog" + (f" label:scope:{folder}" if folder else "")
    try:
        return [i["url"] for i in json.loads(gh("issue", "list", "--state", "open", "--search", search, "--json", "url", cwd=cwd))]
    except (RuntimeError, ValueError, KeyError, TypeError):
        return None


def labels(cwd, n):
    """The label names of issue `n` of `cwd`'s repository."""
    return [label["name"] for label in json.loads(gh("issue", "view", str(n), "--json", "labels", cwd=cwd))["labels"]]


def task(cwd, n):
    """Issue `n` of `cwd`'s repository: its state, label names, body, and the url of each blocker by blocked-by still open."""
    issue = json.loads(gh("issue", "view", str(n), "--json", "state,labels,body", cwd=cwd))
    blockers = json.loads(gh("api", f"repos/{{owner}}/{{repo}}/issues/{n}/dependencies/blocked_by", cwd=cwd) or "[]")
    return {"state": issue["state"], "labels": [label["name"] for label in issue["labels"]], "body": issue.get("body") or "",
            "blockers": [b["html_url"] for b in blockers if b.get("state") == "open"]}


def heads(cwd, state, *repo):
    """The head branch of each `state` pull request, `open`, `merged` or `all`, of `cwd`'s repository, or of `-R <repo>` given as `repo`."""
    return gh("pr", "list", *repo, "--state", state, "--limit", "1000", "--json", "headRefName", "-q", ".[].headRefName", cwd=cwd).split()

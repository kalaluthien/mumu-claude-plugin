"""Reads issues, comments and pull requests of a repository by REST, which spends no GraphQL point, in the shapes `gh issue list --json` gave."""
import json
import re
import subprocess
from urllib.parse import quote

# the keywords GitHub links a pull request to the issue it closes by
CLOSES = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)", re.I)
# a comment read per issue costs a call each, the repository's comments one call a hundred
PER_ISSUE_LIMIT = 40


def get(path, repo=None, paginate=True, tries=3):
    """The parsed JSON of a GET, every page joined when PAGINATE; None when it failed. REPO is `owner/name`, else the checkout's."""
    path = path.replace("repos/", f"repos/{repo}/", 1) if repo else path.replace("repos/", "repos/{owner}/{repo}/", 1)
    for _ in range(tries):  # gh's calls fail now and then, then pass on retry
        p = subprocess.run(["gh", "api", *(["--paginate", "--slurp"] if paginate else []), path], capture_output=True, text=True)
        if p.returncode == 0:
            out = json.loads(p.stdout)
            return [x for page in out for x in page] if paginate else out
    return None


def issue(raw):
    """RAW, a REST issue or pull request, in the shape of a `gh issue list` row."""
    merged = (raw.get("pull_request") or {}).get("merged_at")
    return {"number": raw["number"], "title": raw["title"], "body": raw["body"] or "", "url": raw["html_url"],
            "state": raw["state"].upper(), "stateReason": (raw.get("state_reason") or "").upper(), "createdAt": raw["created_at"],
            "closedAt": raw["closed_at"], "labels": [{"name": x["name"]} for x in raw["labels"]],
            "isPullRequest": "pull_request" in raw, "mergedAt": merged, "comments": []}


def comment(raw):
    return {"body": raw["body"], "url": raw["html_url"], "createdAt": raw["created_at"]}


def with_comments(found, repo=None):
    """FOUND with each row's comments; None when a read failed."""
    pending = [i for i in found if i["comments"] == [] and i["_count"]]
    if len(pending) > PER_ISSUE_LIMIT:
        every = get("repos/issues/comments?per_page=100", repo)
        if every is None:
            return None
        by = {}
        for c in every:
            by.setdefault(int(c["issue_url"].rsplit("/", 1)[1]), []).append(comment(c))
        for i in pending:
            i["comments"] = by.get(i["number"], [])
    else:
        for i in pending:
            read = get(f"repos/issues/{i['number']}/comments?per_page=100", repo)
            if read is None:
                return None
            i["comments"] = [comment(c) for c in read]
    for i in found:
        del i["_count"]
    return found


def issues(state="open", label=None, repo=None, pulls=False, comments=True):
    """The repository's issues, and its pull requests too when PULLS, newest first; None when a read failed."""
    path = f"repos/issues?state={state}&per_page=100" + (f"&labels={quote(label)}" if label else "")
    raw = get(path, repo)
    if raw is None:
        return None
    found = [{**issue(r), "_count": r["comments"]} for r in raw if pulls or "pull_request" not in r]
    return with_comments(found, repo) if comments else [{k: v for k, v in i.items() if k != "_count"} for i in found]


def fresh(number, repo=None):
    """One issue with its comments, read now; None when a read failed."""
    raw = get(f"repos/issues/{number}", repo, paginate=False)
    return raw and (with_comments([{**issue(raw), "_count": raw["comments"]}], repo) or [None])[0]


def pulls(state="open", repo=None, limit=None, branch=None):
    """Pull requests as `number`, `headRefName`, `headRefOid`, `mergedAt`, newest update first; LIMIT cuts it to one page, BRANCH to one head. None when a read failed."""
    raw = get(f"repos/pulls?state={state}&sort=updated&direction=desc&per_page={limit or 100}" + (f"&head={{owner}}:{branch}" if branch else ""),
              repo, paginate=not limit)
    return raw and [{"number": p["number"], "headRefName": p["head"]["ref"], "headRefOid": p["head"]["sha"], "mergedAt": p["merged_at"]} for p in raw]


def conflicts(number, repo=None):
    """Whether the pull request cannot merge cleanly, as `gh pr list` said `CONFLICTING`; None when a read failed."""
    raw = get(f"repos/pulls/{number}", repo, paginate=False)
    return raw and raw["mergeable_state"] == "dirty"

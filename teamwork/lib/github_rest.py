"""Reads issues, comments and pull requests of a repository by REST, which spends no GraphQL point, in the shapes `gh issue list --json` gave."""
import json
import re
import subprocess
from urllib.parse import quote

# the keywords GitHub links a pull request to the issue it closes by
CLOSES = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)", re.I)


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
            "closedAt": raw["closed_at"], "authorAssociation": raw["author_association"], "labels": [{"name": x["name"]} for x in raw["labels"]],
            "isPullRequest": "pull_request" in raw, "mergedAt": merged, "comments": []}


def comment(raw):
    return {"body": raw["body"], "url": raw["html_url"], "createdAt": raw["created_at"], "authorAssociation": raw["author_association"]}


def with_comments(found, repo=None):
    """FOUND with each row's comments, from one paginated read of the repository's comments since the oldest row that has any; None when a read failed."""
    pending = [i for i in found if i["_count"]]
    if pending:
        # a comment is updated no earlier than its issue was created, so this stamp leaves none out
        every = get(f"repos/issues/comments?per_page=100&since={min(i['createdAt'] for i in pending)}", repo)
        if every is None:
            return None
        by = {}
        for c in every:
            by.setdefault(int(c["issue_url"].rsplit("/", 1)[1]), []).append(comment(c))
        for i in pending:
            i["comments"] = by.get(i["number"], [])
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
    """One issue with its comments, read now by its own two reads; None when a read failed."""
    raw, read = get(f"repos/issues/{number}", repo, paginate=False), get(f"repos/issues/{number}/comments?per_page=100", repo)
    return raw and read is not None and {**issue(raw), "comments": [comment(c) for c in read]} or None


def pulls(state="open", repo=None, limit=None, branch=None):
    """Pull requests as `number`, `headRefName`, `headRefOid`, `mergedAt`, newest update first; LIMIT cuts it to one page, BRANCH to one head. None when a read failed."""
    raw = get(f"repos/pulls?state={state}&sort=updated&direction=desc&per_page={limit or 100}" + (f"&head={{owner}}:{branch}" if branch else ""),
              repo, paginate=not limit)
    return raw and [{"number": p["number"], "headRefName": p["head"]["ref"], "headRefOid": p["head"]["sha"], "mergedAt": p["merged_at"]} for p in raw]


def conflicts(number, repo=None):
    """Whether the pull request cannot merge cleanly, as `gh pr list` said `CONFLICTING`; None when a read failed or GitHub has not worked it out yet."""
    raw = get(f"repos/pulls/{number}", repo, paginate=False)
    if raw is None or raw["mergeable_state"] == "unknown":
        return None
    return raw["mergeable_state"] == "dirty"

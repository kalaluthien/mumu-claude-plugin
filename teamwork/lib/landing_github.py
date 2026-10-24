"""Changes on GitHub: pull requests read by REST, which spends no GraphQL point."""
import re

from board_github import changed_since, get  # one GitHub REST reader for both ports, whose issues read counts pull requests too

# the keywords GitHub links a pull request to the issue it closes by
CLOSES = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)", re.I)


def pulls(state="open", repo=None, limit=None, branch=None):
    """Pull requests as `number`, `headRefName`, `headRefOid`, `mergedAt`, newest update first; LIMIT cuts it to one page, BRANCH to one head. None when a read failed."""
    raw = get(f"repos/pulls?state={state}&sort=updated&direction=desc&per_page={limit or 100}" + (f"&head={{owner}}:{branch}" if branch else ""),
              repo, paginate=not limit)
    return raw and [{"number": p["number"], "headRefName": p["head"]["ref"], "headRefOid": p["head"]["sha"], "mergedAt": p["merged_at"]} for p in raw]


def conflicts(number, repo=None):
    """Whether the pull request cannot merge cleanly; None when a read failed or GitHub has not worked it out yet."""
    raw = get(f"repos/pulls/{number}", repo, paginate=False)
    if raw is None or raw["mergeable_state"] == "unknown":
        return None
    return raw["mergeable_state"] == "dirty"


def first_commit(number, repo=None):
    """When the pull request's first commit was authored, by the one commit its list starts with; None when it has none.
    It raises LookupError when the read failed."""
    commits = get(f"repos/pulls/{number}/commits?per_page=1", repo, paginate=False)
    if commits is None:
        raise LookupError(f"the commits of #{number} could not be read")
    return commits[0]["commit"]["author"]["date"] if commits else None

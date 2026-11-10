"""The landing: the changes a worker proposes for its base. Each is a record in local git, read by `landing_git`, whose functions this module re-exports by the same names,
and a merged pull request counts as a change merged, read by `landing_github`, for a repository that lands by pull request.

`pulls(state, repo, limit, branch)` is `number`, `headRefName`, `headRefOid`, `mergedAt`; `conflicts(number, repo)`;
`first_commit(number, repo)`; `changed_since(stamp)`, whether a change moved since an ISO time; and `CLOSES`, the pattern of the words by which a change closes an issue. Branch, change, judge and merge stay
agent steps, done as the landing document says."""
import landing_git
import landing_github


def pulls(state="open", repo=None, limit=None, branch=None):
    """The local changes of STATE, and for a state that holds merged ones the merged pull requests too, newest merge first; an open change is local only."""
    found = landing_git.pulls(state, repo, limit, branch)
    if found is None or state == "open":
        return found
    return sorted([*found, *landing_github.merged(limit, branch)], key=lambda pull: pull["mergedAt"] or "", reverse=True)[:limit]


def changed_since(stamp):
    return landing_git.changed_since(stamp) or landing_github.changed_since(stamp)


def __getattr__(name):
    return getattr(landing_git, name)

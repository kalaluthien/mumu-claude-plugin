"""The landing: the changes a worker proposes for its base, done in local git by `landing_git`, whose functions this module re-exports by the same names.

`pulls(state, repo, limit, branch)` is `number`, `headRefName`, `headRefOid`, `mergedAt`; `conflicts(number, repo)`;
`first_commit(number, repo)`; `changed_since(stamp)`, whether a change moved since an ISO time; and `CLOSES`, the pattern of the words by which a change closes an issue. Branch, change, judge and merge stay
agent steps, done as the landing document says."""
import landing_git


def __getattr__(name):
    return getattr(landing_git, name)

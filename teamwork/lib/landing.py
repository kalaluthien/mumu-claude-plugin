"""The landing port: the changes a worker proposes for its base, done by the adapter `landing_<TEAMWORK_LANDING>` (default `github`).

Every adapter has `pulls(state, repo, limit, branch)` as `number`, `headRefName`, `headRefOid`, `mergedAt`; `conflicts(number, repo)`;
`first_commit(number, repo)`; and `CLOSES`, the pattern of the words by which a change closes an issue. Branch, change, judge and merge stay
agent steps, done as the landing adapter's document says."""
import importlib
import os

adapter = importlib.import_module(f"landing_{os.environ.get('TEAMWORK_LANDING', 'github')}")


def __getattr__(name):
    return getattr(adapter, name)

"""The landing port: the changes a worker proposes for its base, done by the adapter `landing_<TEAMWORK_LANDING>`, read from the environment, else from the project's Claude settings `env` (default `github`).

Every adapter has `pulls(state, repo, limit, branch)` as `number`, `headRefName`, `headRefOid`, `mergedAt`; `conflicts(number, repo)`;
`first_commit(number, repo)`; `changed_since(stamp)`, whether a change moved since an ISO time; and `CLOSES`, the pattern of the words by which a change closes an issue. Branch, change, judge and merge stay
agent steps, done as the landing adapter's document says."""
import importlib
import port_setting


def kind():
    """The adapter's name, read at each call, so a long-running process follows a setting written after it started."""
    return port_setting.value("TEAMWORK_LANDING", "github")


def __getattr__(name):
    return getattr(importlib.import_module(f"landing_{kind()}"), name)

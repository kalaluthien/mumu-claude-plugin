"""What a session's name says in a team: its role, its project, the branches it owns, and its workspace's members."""


def role(name):
    """`manager`, `worker` or `sentinel` by the name's suffix; None for a name with none, a session outside any team, such as the owner's own."""
    return next((r for r in ("manager", "worker", "sentinel") if (name or "").endswith("-" + r)), None)


def project(manager):
    return manager.removesuffix("-manager")


def owns(name, branch):
    # a repository's rules may put a prefix such as `feature/` before the worker's name
    last = branch.rsplit("/", 1)[-1]
    return last == name or last.startswith(name + "-")


def members(me, listed):
    """The workers and other sessions in your workspace; never a manager, since each manager is alone with its workers there."""
    return [a["name"] for a in listed if a.get("workspace_id") == me.get("workspace_id") and a is not me and a.get("name") and role(a["name"]) != "manager"]


def workers(me, listed):
    """The workers in your workspace, which a manager's exit waits on; a sentinel judges alone what to do once its manager ends."""
    return [n for n in members(me, listed) if role(n) == "worker"]


def crowding(me, listed):
    """The managers of another project in your workspace."""
    return [a["name"] for a in listed if a.get("workspace_id") == me.get("workspace_id") and role(a.get("name")) == "manager"
            and project(a["name"]) != project(me.get("name", ""))]

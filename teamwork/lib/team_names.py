"""What a session's name says in a team: its role, its project, the branches it owns, and its workspace's members."""


def role(name):
    """`manager`, `worker` or `sentinel` by the name's suffix; None for a name with none, a session outside any team, such as the owner's own."""
    return next((candidate for candidate in ("manager", "worker", "sentinel") if (name or "").endswith("-" + candidate)), None)


def project(manager):
    return manager.removesuffix("-manager")


def owns(name, branch):
    # a repository's rules may put a prefix such as `feature/` before the worker's name
    last = branch.rsplit("/", 1)[-1]
    return last == name or last.startswith(name + "-")


def members(me, listed):
    """The workers and sentinels in your workspace; never a manager, since each manager is alone with its workers there, nor a session
    with no role, such as a probe a worker started or the owner's own, which the manager started not and cannot answer."""
    return [agent["name"] for agent in listed if agent.get("workspace_id") == me.get("workspace_id") and agent is not me and role(agent.get("name")) in ("worker", "sentinel")]


def watching(me, listed):
    """Whether the session has a team to watch: a worker always, a manager while a worker lives in its workspace, any other session never."""
    kind = role(me.get("name"))
    return kind == "worker" or kind == "manager" and any(role(name) == "worker" for name in members(me, listed))


def crowding(me, listed):
    """The managers of another project in your workspace."""
    return [agent["name"] for agent in listed if agent.get("workspace_id") == me.get("workspace_id") and role(agent.get("name")) == "manager"
            and project(agent["name"]) != project(me.get("name", ""))]

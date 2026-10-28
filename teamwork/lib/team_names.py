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
    """The workers and other sessions in your workspace; never a manager, since each manager is alone with its workers there."""
    return [agent["name"] for agent in listed if agent.get("workspace_id") == me.get("workspace_id") and agent is not me and agent.get("name") and role(agent["name"]) != "manager"]


def workers(me, listed):
    """The workers in your workspace, which a manager's exit waits on; a sentinel judges alone what to do once its manager ends."""
    return [name for name in members(me, listed) if role(name) == "worker"]


def crowding(me, listed):
    """The managers of another project in your workspace."""
    return [agent["name"] for agent in listed if agent.get("workspace_id") == me.get("workspace_id") and role(agent.get("name")) == "manager"
            and project(agent["name"]) != project(me.get("name", ""))]

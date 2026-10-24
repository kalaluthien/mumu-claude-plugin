"""What a session's name says in a team: its role, its project, the branches it owns, and its workspace's members."""


def role(name):
    """`manager` or `worker` by the name's suffix; None for a name with neither, a session outside any team, such as the owner's own."""
    return next((r for r in ("manager", "worker") if (name or "").endswith("-" + r)), None)


def project(manager):
    return manager.removesuffix("-manager")


def owns(name, branch):
    # a repository's rules may put a prefix such as `feature/` before the worker's name
    last = branch.rsplit("/", 1)[-1]
    return last == name or last.startswith(name + "-")


def members(me, listed):
    return [a["name"] for a in listed if a.get("workspace_id") == me.get("workspace_id") and a is not me and a.get("name")]

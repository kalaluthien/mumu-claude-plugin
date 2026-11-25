"""The time order of one level of a flow contract: what comes before what, where each record falls on the time axis, and a plan's
critical path, the longest chain of predecessors, counted in tasks."""


def timed(contract, level):
    """The ids of LEVEL's timed records in the contract's order: its edges for an interaction, its tasks for a plan, then its milestones."""
    kind = "edges" if level["kind"] == "interaction" else "tasks"
    return [record["id"] for record in contract.get(kind, []) if record.get("level") == level["id"]] + \
           [milestone["id"] for milestone in contract.get("milestones", []) if milestone.get("level") == level["id"]]


def before(contract, level):
    """Each timed record of LEVEL by id, with the ids that must come before it: what its `after` names; for an interaction each edge
    follows the edge listed before it, and for a plan an edge's `to` task follows its `from` task."""
    ids = timed(contract, level)
    first = {name: set() for name in ids}
    records = [record for kind in ("edges", "tasks", "milestones") for record in contract.get(kind, []) if record.get("level") == level["id"]]
    for record in records:
        if record["id"] in first:
            first[record["id"]] |= {name for name in record.get("after", []) if name in first}
    if level["kind"] == "interaction":
        edges = [record["id"] for record in contract.get("edges", []) if record.get("level") == level["id"]]
        for earlier, later in zip(edges, edges[1:]):
            first[later].add(earlier)
    else:
        for edge in contract.get("edges", []):
            if edge.get("level") == level["id"] and edge.get("from") in first and edge.get("to") in first:
                first[edge["to"]].add(edge["from"])
    return first


def cycle(first):
    """A list of ids that each come before the next and the last before the first, or None when the order FIRST gives has no cycle."""
    state = {}
    for start in first:  # a start walked before is walked again, finding every id after it done
        trail, stack = [], [(start, iter(sorted(first[start])))]
        state[start] = "open"
        trail.append(start)
        while stack:
            name, rest = stack[-1]
            following = next(rest, None)
            if following is None:
                state[name] = "done"
                stack.pop()
                trail.pop()
            elif state.get(following) == "open":
                return list(reversed(trail[trail.index(following):]))
            elif following not in state:
                state[following] = "open"
                trail.append(following)
                stack.append((following, iter(sorted(first[following]))))
    return None


def followers(first):
    """Each id of FIRST with the ids that come right after it, in FIRST's order."""
    later = {name: [] for name in first}
    for other in first:
        for name in first[other]:
            later[name].append(other)
    return later


def walked(first, later):
    """FIRST's ids, each after every id that comes before it, by a loop rather than recursion, so a chain of any length is walked.
    FIRST holds no cycle."""
    waiting = {name: len(first[name]) for name in first}
    found = [name for name in first if not waiting[name]]
    for name in found:
        for other in later[name]:
            waiting[other] -= 1
            if not waiting[other]:
                found.append(other)
    return found


def ranks(first):
    """Each id's place on the time axis, counted from 0: one past the latest of what comes before it. FIRST holds no cycle."""
    rank = {}
    for name in walked(first, followers(first)):
        rank[name] = max((rank[earlier] + 1 for earlier in first[name]), default=0)
    return {name: rank[name] for name in first}


def critical(first, tasks):
    """The longest chain of predecessors in FIRST, each id coming right before the next, counted by how many of TASKS it holds; of equal
    chains, the one that starts and goes on earliest in FIRST's order. FIRST holds no cycle."""
    later = followers(first)
    held, following = {}, {}
    for name in reversed(walked(first, later)):
        tail = max(later[name], key=lambda other: held[other], default=None)
        held[name] = (name in tasks) + (held[tail] if tail is not None else 0)
        following[name] = tail
    starts = [name for name in first if not first[name]]
    name = max(starts, key=lambda start: held[start], default=None)
    chain = []
    while name is not None:
        chain.append(name)
        name = following[name]
    return chain

"""The `rebalance` lines of a manager's heartbeat: a worker with a queue of waiting tasks, and a task that waits on another only for a file both change."""
import re

QUEUE = 3  # tasks one worker holds that each wait on a task, from which its queue is worth rebalancing
CAP = 4  # live workers per team, the owner's word on #1552
COVERS = re.compile(r"covers:\s*`([^`]*)`")


def files(task):
    """The files its criteria say they cover."""
    return {name.strip() for text in COVERS.findall(task.get("body") or "") for name in text.split(",") if name.strip()}


def shared_files(task, blocker):
    """The files TASK and the task it waits on both cover, when TASK's body never names that task, since a task that names it waits for its result; else none."""
    return set() if re.search(rf"#{blocker['number']}\b", task.get("body") or "") else files(task) & files(blocker)


def lines(queues, open_tasks, blockers, live):
    """The lines for QUEUES, each worker's open tasks that wait on a task, OPEN_TASKS by number, BLOCKERS, each task's unfinished blockers, and LIVE workers."""
    found = []
    for name, queue in queues.items():
        if len(queue) >= QUEUE:
            room = (f"{live} of {CAP} live workers: start a worker at the cheapest fitting tier for unrelated waiting work" if live < CAP
                    else f"the team is at the cap of {CAP} live workers: ask the owner to pass it")
            found.append(f"rebalance {name} holds {' '.join(f'#{number}' for number in queue)}, each waiting on a task: fold the ones that change the same code into one change, split unrelated parts, "
                         f"keep a wait only for a needed result, move up the task others wait on; {room}; as the manager playbook's Rebalance rule says")
    for number, waits in sorted(blockers.items()):
        for blocker in waits:
            shared = shared_files(open_tasks[number], open_tasks[blocker]) if number in open_tasks and blocker in open_tasks else set()
            if shared:
                found.append(f"rebalance #{number} waits on #{blocker} only for {', '.join(sorted(shared))}, which both change: fold them into one change, or split them so each runs at once; as the manager playbook's Rebalance rule says")
    return found

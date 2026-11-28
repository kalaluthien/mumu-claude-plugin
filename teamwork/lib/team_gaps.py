"""Each role's next actions: the gaps between the board's tasks and the live team, as lines a monitor or hook prints."""

import os
import re
import time

import background_work
import board
import board_text
import decisions
import record_types
import task_state
import landing
import remote_control
import task_links
import team_balance
from session import screen, sessions, tabs
from team_names import crowding, members, owns, project, role

PULL_LIMIT = 50
STUCK_SECONDS = float(os.environ.get("TEAMWORK_STUCK_SECONDS", 900))  # a run that waits this long with no CPU waits on what never comes, or on the owner
SLOW_SECONDS = float(os.environ.get("TEAMWORK_SLOW_SECONDS", 3600))  # a check run this long holds its worker idle, so the manager weighs a narrower one

# the reports a worker posts as steps of its own work, which the owner need not follow: [run-criteria.py](../skills/kick-off/scripts/run-criteria.py)'s table and a filed task
STEP_REPORTS = ("criteria at ", "task filed")


def tasks(scope=None, state="open"):
    try:
        return board.tasks(state, scope)
    except LookupError:  # a session whose folder lies outside a repository has no board to read, as a failed read has none
        return None


def holds(task, name):
    """Whether NAME's record holds TASK, as recorded, since it asks of a live session, for which the recorded and the live holders agree."""
    return name in ((task_state.holder_values(task) or [[]])[-1])


def asking(task):
    return bool(task_state.open_questions(task))


def wait_blockers(numbers, open_tasks):
    """Each of the open tasks NUMBERS and each of their open parts, mapped to the tasks it depends on that are not closed as completed;
    None when a read failed. A caller keeps it with its read, since each task costs a board read."""
    wanted = {number for task in numbers for number in [task, *task_links.parts(open_tasks[task]["body"])] if number in open_tasks}
    found = {number: board.blockers(number) for number in wanted}
    return None if None in found.values() else found


def waiting(task, open_tasks, blockers):
    """Whether an open task waits, as the grammar's Waits states: BLOCKERS, a `wait_blockers`, holds a task for it, or for each of its open parts."""
    parts = [number for number in task_links.parts(task["body"]) if number in open_tasks]
    return bool(blockers.get(task["number"])) or bool(parts) and all(blockers.get(number) for number in parts)


def stalled(task, open_tasks, blockers):
    """Whether a held task waits on no one: not on another open task, nor on an answer."""
    return not waiting(task, open_tasks, blockers) and not asking(task)


def background(agent):
    """Whether a session has a subagent or a command running in the background, which it waits on while its status reads idle."""
    session_id = (agent.get("agent_session") or {}).get("value")
    transcript = background_work.transcript_of(session_id)
    return bool(transcript and background_work.running_work(transcript)) or bool(background_work.running_commands(session_id))


def feed_read(name, since):
    """The reports posted since SINCE (an ISO time) on this manager's project's open roots and parents and on its tasks closed now, as (task, comment);
    None when a read failed. A task's other reports, such as each precheck table, are steps the owner need not follow."""
    touched = board.tasks("all", project(name), comments=False, since=since)
    posted = board.comments_since(since)
    if touched is None or posted is None:
        return None
    by = {task["number"]: task for task in touched if task["state"] != "open" or task["parent"] is None or task_links.parts(task["body"])}
    # `since` matches an edit too, so an old comment edited now is left out by its creation time
    found = [(by[number], comment) for number, comment in posted
             if number in by and comment["created"] >= since and comment["kind"] == "report" and not task_state.first_line(comment).startswith(STEP_REPORTS)]
    # a closed task's last report is its close summary
    last = {task["number"]: comment["url"] for task, comment in found}
    return [(task, comment) for task, comment in found if task["state"] == "open" or last[task["number"]] == comment["url"]]


def manager_read(me, since=None):
    """What a manager's gaps need from the board, read once and kept by the caller until something changed; None when a read failed.
    SINCE adds the reports posted since then."""
    found = tasks(project(me["name"]))
    if found is None:  # the first read failed, or the folder lies outside a repository: the reads below would fail the same way
        return None
    # a worker may hold an open task outside the project's folder, which the idle line must still count
    everything = tasks() if found is not None else found
    # one page of the latest updated closed pulls, whose merged ones are the newest merges
    pulls = landing.pulls("closed", limit=PULL_LIMIT)
    pulls = pulls and [pull for pull in pulls if pull["mergedAt"]]
    feed = feed_read(me["name"], since) if since else []  # a first read has no earlier one, so a restart pushes nothing old
    # a failed tree read costs only the link lines
    tree = board.tree(project(me["name"]))
    links = task_links.drift(tree) if tree is not None else ["unread: the board's tree read failed, so link gaps are not checked this time"]
    if found is None or everything is None or pulls is None or feed is None:
        return None
    open_tasks = {task["number"]: task for task in [*everything, *found]}
    blockers = wait_blockers(open_tasks, open_tasks)
    if blockers is None:
        return None
    return {"found": found, "everything": everything, "prs": pulls, "feed": feed, "links": links, "blockers": blockers}


def manager_actions(me, listed, data=None, fed_urls=None, readings=None):
    """A manager's gaps from DATA, a `manager_read` kept from an earlier poll, else from a read now. FED_URLS, kept by the caller
    across polls, holds the urls of the reports already fed, since two reads overlap by the clock skew; READINGS, kept likewise, holds
    each team run's last CPU reading, and without it no run is called stuck."""
    data = data or manager_read(me)
    if data is None:
        return None
    team = members(me, listed)
    found = data["found"]
    lines = []
    if crowd := crowding(me, listed):
        lines.append(f"shared workspace: {', '.join(crowd)} manage another project in your workspace; move to a workspace of your own: "
                     f"`start` `{me['name']}-next` with `succeed {me['name']}`, as Succession says, which opens one")
    # a started worker names its tab before its agent is live, so its tab counts it as routed
    present = set(team) | {tab.get("label") for tab in tabs(me.get("workspace_id", ""))}
    again = Reread(me)
    open_tasks = {task["number"]: task for task in [*data["everything"], *found]}
    blockers = data.get("blockers") or wait_blockers(open_tasks, open_tasks)
    if blockers is None:
        return None
    lines += routing_lines(found, present, open_tasks, blockers, again)
    lines += [f"links {gap}" for gap in data.get("links", [])]
    lines += decisions.gaps(found)
    lines += team_lines(team, listed, data, open_tasks, blockers, again)
    lines += rebalance_lines(team, open_tasks, blockers)
    lines += run_lines(team, listed, readings)
    return lines + feed_lines(me, data, fed_urls)


class Reread:
    """The sessions read again, once and only when a line is about to print, since the poll's own read may predate a worker's start or a change of its status;
    a read the host failed gives nothing, which disproves no line."""

    def __init__(self, me):
        self.me, self.listed = me, None

    def sessions(self):
        if self.listed is None:
            self.listed = sessions()[0]
        return self.listed

    def present(self):
        listed = self.sessions()
        return set(members(self.me, listed)) | {tab.get("label") for tab in tabs(self.me.get("workspace_id", ""))} if listed else None

    def holding(self, name):
        """The open tasks NAME holds from a read now; None when it failed."""
        found = tasks()
        return found and [task for task in found if holds(task, name)]

    def status(self, name):
        return next((agent.get("agent_status") for agent in self.sessions() if agent.get("name") == name), None)


def routing_lines(found, present, open_tasks, blockers, again):
    """Per open task, a route line while no live worker in PRESENT holds it and an answer line while its worker asks.
    AGAIN, a `Reread`, confirms a task that looks unrouted against a read now."""
    lines = []
    unrouted = lambda task, names: not waiting(task, open_tasks, blockers) and not any(holds(task, name) for name in names if name)
    for task in found:
        # the kept read may predate the manager's own `decide`, so a candidate is read again before it is called unrouted
        if unrouted(task, present) and (names := again.present()) is not None and unrouted(board.fresh(task["number"]) or task, names):
            lines.append(board_text.line(f"route #{task['number']} is held by no live worker: route it, or name by `depend` the open task it waits for, or close it as not planned;", title=task["title"]))
        # the kept read may predate the manager's own `decide`, so a question is read again before it is called open
        if asking(task) and asking(board.fresh(task["number"]) or task):
            ask = task_state.open_questions(task)[-1]["ask"]
            lines.append(f"answer #{task['number']}: its worker asks at {ask['url']}; answer by `decide` there with `--answers {ask['url']}`; "
                         f"the worker waits on it")
    return lines


def team_lines(team, listed, data, open_tasks, blockers, again):
    """Per worker or sentinel in TEAM, the line for its pane: blocked at a prompt, merged with nothing held, or idle with nothing to do."""
    status = {agent.get("name"): agent.get("agent_status") for agent in listed}
    panes = {agent.get("name"): agent.get("pane_id") for agent in listed}
    by_name = {agent.get("name"): agent for agent in listed}
    lines = []
    merged = {name: [pull["number"] for pull in data["prs"] if owns(name, pull["headRefName"])] for name in team}
    for name in team:
        held_tasks = [task for task in data["everything"] if holds(task, name)]
        held = " ".join(f"#{task['number']}" for task in held_tasks) or "nothing open"
        choices = prompt_text(panes[name]) if status[name] == "blocked" and again.status(name) == "blocked" else None  # a blocked pane with no prompt on it is no claim on the worker, so its merged change still shows
        if choices:
            lines.append(f"blocked {name} (pane {panes[name]}): it waits at a tool-use prompt; tell the owner this screen, then answer by the manager's Triage row for a tool prompt once the owner says so: {choices}")
        elif merged[name] and not held_tasks and again.holding(name) == []:
            # a merged change is news only once its worker has nothing left to do, since until then the worker goes on with its next task
            lines.append(f"merged {' '.join(f'#{number}' for number in merged[name])} by {name}: it holds nothing open; close it and clean its worktree")
        elif status[name] in ("idle", "done") and role(name) != "sentinel" and (not held_tasks or any(stalled(task, open_tasks, blockers) for task in held_tasks)) \
                and not background(by_name[name]) and again.status(name) in ("idle", "done") \
                and (held_tasks or again.holding(name) == []):
            # a sentinel waits idle between the rounds of its duty; a worker whose tasks all wait on a task, the owner or the manager has nothing to do yet
            lines.append(f"idle {name}: holds {held}; give it its next step, answer what it waits on, or close it when it holds nothing open")
    return lines


def rebalance_lines(team, open_tasks, blockers):
    """The rebalance lines for the tasks each live worker holds that wait on a task."""
    workers = [name for name in team if not name.endswith("-sentinel")]
    queues = {name: [number for number, task in open_tasks.items() if holds(task, name) and blockers.get(number)] for name in workers}
    return team_balance.lines(queues, open_tasks, blockers, len(workers))


def run_lines(team, listed, readings):
    """Per process tree a session in TEAM runs, a stuck line once it has used no CPU for STUCK_SECONDS, and a slow line once a
    `run-criteria.py` in it passes SLOW_SECONDS. READINGS maps each run to its last reading and the time it was first read so,
    which this updates; None reads no CPU."""
    session_of = {agent.get("name"): (agent.get("agent_session") or {}).get("value") for agent in listed}
    found = background_work.runs([session_of.get(name) for name in team])
    now, lines, seen = time.monotonic(), [], set()
    readings = {} if readings is None else readings  # the hook's one-shot call keeps none, so no run reads as stuck there
    for name in team:
        for pid, command, reading, criteria in found.get(session_of.get(name), []):
            key = pid  # a process id is unique on the machine, so it keeps two runs of one session apart
            seen.add(key)
            last, since = readings.get(key, (None, now))
            readings[key] = (reading, since if last == reading else now)
            if now - readings[key][1] >= STUCK_SECONDS:
                lines.append(f"stuck {name}: pid {pid} (`{command}`) has used no CPU for {STUCK_SECONDS / 60:g} minutes; ask {name} what it waits on, "
                             f"and to stop it by TaskStop or `kill {pid}` and name the cause on its task if it hangs")
            if criteria and criteria[0] >= SLOW_SECONDS:
                lines.append(f"slow {name}: `{criteria[1]}` has run over {SLOW_SECONDS / 60:g} minutes; ask {name} whether its progress lines still move, "
                             f"and weigh a narrower run, such as `--since <sha>` or fewer criteria")
    for key in set(readings) - seen:
        del readings[key]
    return lines


def feed_lines(me, data, fed_urls):
    """A line per task with reports not yet fed to this manager; FED_URLS, when given, records the urls fed."""
    news = {}
    for task, comment in data.get("feed", []):
        # what this manager posted itself is no news to it
        if fed_urls is not None and comment["url"] not in fed_urls and comment["author"] != me["name"]:
            fed_urls.add(comment["url"])
            news.setdefault(task["number"], (task, []))[1].append(comment)
    lines = []
    for task, posted in news.values():
        said = " | ".join(record_types.shown(comment).strip().splitlines()[0] for comment in posted)
        # a push reaches the owner away only through Remote Control, so without it the line sends none
        push = "push it to the owner by PushNotification" if remote_control.active((me.get("agent_session") or {}).get("value")) else "tell the owner in your tab; send no push, since Remote Control is off in your session"
        lines.append(board_text.line(f"feed #{task['number']} has a report ({posted[-1]['url']}): {push};", title=task["title"], report=said))
    return lines


def prompt_text(pane):
    """A blocked pane's prompt on one line: its question and numbered choices, from the line above the first choice to the hint row after the last
    (`Esc to cancel`, `Enter to select`), without what the footer adds after it; None when the screen shows no choice, such as an empty input
    under a banner, which is no prompt to answer."""
    lines = [line.strip() for line in screen(pane).splitlines() if line.strip() and not set(line.strip()) <= set("─╌━ ")]
    choices = [at for at, line in enumerate(lines) if re.match(r"^\W*1\. ", line)]
    if not choices:
        return None
    start = choices[-1]
    # a footer hint that comes and goes, such as the one for background agents, would make the same prompt read as a new line
    hints = [at for at in range(start, min(len(lines), start + 14)) if re.match(r"^(Esc|Enter)\b", lines[at])]
    shown = lines[max(0, start - 2):hints[0] if hints else start + 7]
    if hints:  # the hint row keeps its first phrase, since the hints after a `·` come and go
        shown.append(re.split(r"\s·\s", lines[hints[0]])[0])
    # the time a prompt has left before it denies itself changes at every poll, so it is not part of the line
    return re.sub(r"(?<=\bin )\d{1,2}:\d\d\b", "…", " | ".join(shown))


def worker_goal(me):
    """Each held task's state from a fresh read, since a list read can lag a comment just posted."""
    every = tasks() or []
    open_tasks = {task["number"]: task for task in every}
    fresh = [board.fresh(task["number"]) or task for task in every if holds(task, me["name"])]
    open_tasks.update((task["number"], task) for task in fresh)
    blockers = wait_blockers([task["number"] for task in fresh], open_tasks) or {}
    return [board_text.line(f"#{task['number']} " + ("waits on your manager" if asking(task) else "waits on a task" if waiting(task, open_tasks, blockers) else "is open")
                            + f" ({task['url']}):", title=task["title"]) for task in fresh]


def worker_read(me):
    """What a worker's wait needs from the board, read once and kept by the caller until something changed; None when a read failed."""
    found = tasks()
    pulls = landing.pulls("open")
    if found is None or pulls is None:
        return None
    for pull in (pull for pull in pulls if owns(me["name"], pull["headRefName"])):  # the list read lacks mergeability, which a pull read gives
        pull["mergeable"] = {True: "CONFLICTING", False: "MERGEABLE"}.get(landing.conflicts(pull["number"]))
    open_tasks = {task["number"]: task for task in found}
    blockers = wait_blockers([task["number"] for task in found if holds(task, me["name"])], open_tasks)
    return None if blockers is None else {"found": found, "prs": pulls, "blockers": blockers}


def changed(task):
    """What a worker reads of a held task: its body and every comment but a report, since a report is the worker's own step or news for the manager."""
    return board.body_sha(task["body"]), [comment["url"] for comment in task["comments"] if comment["kind"] != "report"]


def acted_on(task, answer):
    """Whether the worker wrote after ANSWER: any later comment that is no decision or event, since only a decider writes those and the worker's own steps are asks, reports and tables."""
    later = task["comments"][task["comments"].index(answer) + 1:]
    return any(comment["kind"] not in ("decision", "event") for comment in later)


def worker_actions(me, waited, read_of, data=None):
    """What ended a wait of this worker, each task it held that changed or no longer names it since the last poll, and a worker holding nothing, as the act it needs;
    None when a read failed.
    WAITED, kept by the caller across polls, holds the held tasks last seen waiting on a task, so only the end of that wait prints.
    READ_OF, kept the same way, maps each held task to what `changed` read, so a restart prints no change that came before it.
    DATA is a `worker_read` kept from an earlier poll, else a read now."""
    data = data or worker_read(me)
    if data is None:
        return None
    name, found, pulls = me["name"], data["found"], data["prs"]
    lines = []
    open_tasks = {task["number"]: task for task in found}
    held = [task for task in found if holds(task, name)]
    check = "read it, then fix any mismatch between its decisions, its `holders` and your progress"
    for number in set(read_of) - {task["number"] for task in held}:
        del read_of[number]
        if number in open_tasks:  # still open and no longer naming this worker
            lines.append(f"changed #{number} (record {len(changed(open_tasks[number])[1])}): {check}")
    if not held and Reread(me).holding(name) == []:  # the kept read may predate the manager's `hold`
        lines.append("holds nothing: no open task names you in its `holders`; read your task and name yourself by `hold`, or close yourself when your work is done")
    for task in held:
        if read_of.setdefault(task["number"], changed(task)) != changed(task):
            read_of[task["number"]] = changed(task)
            lines.append(f"changed #{task['number']} (record {len(changed(task)[1])}): {check}")  # the count makes each change its own line, which the monitor prints once
        latest = task_state.questions(task)[-1:]
        if latest and latest[0]["answer"] and not acted_on(task, latest[0]["answer"]):
            lines.append(f"answered #{task['number']}: {latest[0]['answer']['url']} answers your {task_state.ASK}:; act on it")
        if waiting(task, open_tasks, data["blockers"]):
            waited.add(task["number"])
        elif task["number"] in waited:
            waited.discard(task["number"])
            lines.append(f"start #{task['number']}: every task it waited on is closed")
    for pull in pulls:
        if owns(name, pull["headRefName"]) and pull.get("mergeable") == "CONFLICTING" and landing.conflicts(pull["number"]):
            lines.append(f"rebase #{pull['number']}: it conflicts with its base")
    return lines

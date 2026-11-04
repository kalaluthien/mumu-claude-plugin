"""Each role's next actions: the gaps between the board's issues and the live team, as lines a monitor or hook prints."""

import re

import background_work
import board
import decisions
import issue_state
import landing
import own_reports
import remote_control
import task_links
from session import screen, tabs
from team_names import crowding, members, owns, project, role

ISSUE_LIMIT, PULL_LIMIT = 200, 50

ASK, ANSWER = issue_state.WORD["ask"], issue_state.WORD["answer"]
FEED = issue_state.INFORM
# the reports a worker posts as steps of its own work, which the owner need not follow: [run-criteria.py](../skills/kick-off/scripts/run-criteria.py)'s table and a filed task
STEP_REPORTS = ("criteria at ", "task filed")


def issues(project=None, state="open"):
    found = board.issues(state, project)
    return found and found[:ISSUE_LIMIT]


def limited(found, limit, what):
    """A line when a list came back full, since the read then drops the rest without a word."""
    return [f"limit: the {what} list returned its limit of {limit}, so some are not shown"] if len(found) >= limit else []


def holds(issue, name):
    return name in (issue_state.compose(issue)["holders"] or [])


def asking(issue):
    return bool(issue_state.open_questions(issue))


def unanswered(issue):
    """An outside contributor's issue or pull request that no trusted `DECIDED:` has routed or answered yet."""
    return (not issue_state.trusted(issue) and not issue_state.holder_values(issue)
            and not any(issue_state.KEYWORDS.get(word) == "answer" for word, _, _ in issue_state.records(issue)[1:]))


def waiting(issue, open_issues):
    """Whether an open task waits on another open task: its own `depends on:` names one, or each of its open parts does."""
    blocked = lambda body: any(number in open_issues for number in task_links.depends(body))
    parts = [open_issues[number] for number in task_links.parts(issue["body"]) if number in open_issues]
    return blocked(issue["body"]) or bool(parts) and all(blocked(part["body"]) for part in parts)


def stalled(issue, open_issues):
    """Whether a held task waits on no one: not on another open task, nor on an answer."""
    return not waiting(issue, open_issues) and not asking(issue)


def background(agent):
    """Whether a session has a subagent or a command running in the background, which it waits on while its status reads idle."""
    transcript = background_work.transcript_of((agent.get("agent_session") or {}).get("value"))
    return bool(transcript and background_work.running_work(transcript))


def feed_read(name, since):
    """The trusted reports posted since SINCE (an ISO time) on this manager's project's open roots and parents and on its issues closed now, as (issue, comment);
    None when a read failed. A task's other reports, such as each precheck table, are steps the owner need not follow."""
    touched = board.issues("all", project(name), comments=False, since=since)
    posted = board.comments_since(since)
    if touched is None or posted is None:
        return None
    by = {issue["number"]: issue for issue in touched if issue["state"] == "CLOSED" or issue["parent"] is None or task_links.parts(issue["body"])}
    # `since` matches an edit too, so an old comment edited now is left out by its creation time
    found = [(by[number], comment) for number, comment in posted
             if number in by and comment["createdAt"] >= since and issue_state.trusted(comment) and issue_state.keyword(comment["body"]) == FEED
             and not comment["body"].split(":", 1)[1].strip().startswith(STEP_REPORTS)]
    # a closed task's last report is its close summary
    last = {issue["number"]: comment["url"] for issue, comment in found}
    return [(issue, comment) for issue, comment in found if issue["state"] == "OPEN" or last[issue["number"]] == comment["url"]]


def manager_read(me, since=None):
    """What a manager's gaps need from the board, read once and kept by the caller until something changed; None when a read failed.
    SINCE adds the reports posted since then."""
    found = issues(project(me["name"]))
    # a worker may hold an open issue outside the project's folder, which the idle line must still count
    everything = issues() if found is not None else found
    # one page of the latest updated closed pulls, whose merged ones are the newest merges
    pulls = landing.pulls("closed", limit=PULL_LIMIT)
    pulls = pulls and [pull for pull in pulls if pull["mergedAt"]]
    # an outside contributor's issue or pull request carries no scope label, so it is read across the repository
    outside = board.issues(pulls=True, comments=False)
    outside = outside and [board.fresh(issue["number"]) for issue in outside if not issue_state.trusted(issue)]
    feed = feed_read(me["name"], since) if since else []  # a first read has no earlier one, so a restart pushes nothing old
    # a failed tree read costs only the link lines
    tree = board.tree(project(me["name"]))
    links = task_links.drift(tree) if tree is not None else ["unread: the board's tree read failed, so link gaps are not checked this time"]
    if found is None or everything is None or pulls is None or outside is None or None in outside or feed is None:
        return None
    return {"found": found, "everything": everything, "prs": pulls, "outside": [issue for issue in outside if unanswered(issue)],
            "feed": feed, "links": links}


def manager_actions(me, listed, data=None, fed_urls=None):
    """A manager's gaps from DATA, a `manager_read` kept from an earlier poll, else from a read now. FED_URLS, kept by the caller
    across polls, holds the urls of the reports already fed, since two reads overlap by the clock skew."""
    data = data or manager_read(me)
    if data is None:
        return None
    team = members(me, listed)
    status = {agent.get("name"): agent.get("agent_status") for agent in listed}
    panes = {agent.get("name"): agent.get("pane_id") for agent in listed}
    by_name = {agent.get("name"): agent for agent in listed}
    found, pulls = data["found"], data["prs"]
    lines = limited(found, ISSUE_LIMIT, "open-issue")  # merged PRs past the newest are always many and no live worker's
    if crowd := crowding(me, listed):
        lines.append(f"shared workspace: {', '.join(crowd)} manage another project in your workspace; move to a workspace of your own: "
                     f"`start` `{me['name']}-next` with `succeed {me['name']}`, as Succession says, which opens one")
    # a started worker names its tab before its agent is live, so its tab counts it as routed
    present = set(team) | {tab.get("label") for tab in tabs(me.get("workspace_id", ""))}
    # a cloud name holds on every open issue, so a task its worker filed itself counts as held though only its root names it cloud
    present |= {name for issue in data["everything"] for name in issue_state.cloud(issue)}
    open_issues = {issue["number"]: issue for issue in [*data["everything"], *found]}
    unrouted = lambda issue: not unanswered(issue) and not waiting(issue, open_issues) and not any(holds(issue, name) for name in present if name)
    for issue in found:
        # the kept read may predate the manager's own `decide`, so a candidate is read again before it is called unrouted
        if unrouted(issue) and unrouted(board.fresh(issue["number"]) or issue):
            lines.append(f"route #{issue['number']} {issue_state.title(issue)}: no live worker holds it; route it, or write in its body `{issue_state.WORD['depends']}:` the open task it waits for, or close it as not planned")
        # the kept read may predate the manager's own `decide`, so a question is read again before it is called open
        if asking(issue) and asking(board.fresh(issue["number"]) or issue):
            ask = issue_state.open_questions(issue)[-1]["ask"]
            lines.append(f"answer #{issue['number']}: its worker asks at {ask['url']}; answer by `decide` there with `{decisions.FIELD['answers']}: {ask['url']}`; "
                         f"the worker waits on it")
    lines += [f"links {gap}" for gap in data.get("links", [])]
    lines += decisions.gaps(found)
    for issue in data["outside"]:
        if issue.get("isPullRequest"):
            lines.append(f"outside #{issue['number']} {issue_state.title(issue)}: an outside contributor opened this pull request; close it unread with a comment that outside pull requests are not accepted and issues are welcome")
        else:
            lines.append(f"outside #{issue['number']} {issue_state.title(issue)}: an outside contributor opened it; ask the owner, then route it, answer it by a {ANSWER}:, or close it")
    merged = {name: [pull["number"] for pull in pulls if owns(name, pull["headRefName"])] for name in team}
    for name in team:
        held_issues = [issue for issue in data["everything"] if holds(issue, name)]
        held = " ".join(f"#{issue['number']}" for issue in held_issues) or "nothing open"
        choices = prompt_text(panes[name]) if status[name] == "blocked" else None  # a blocked pane with no prompt on it is no claim on the worker, so its merged change still shows
        if choices:
            lines.append(f"blocked {name} (pane {panes[name]}): it waits at a tool-use prompt; tell the owner this screen, then answer by the Tool prompt rule once the owner says so: {choices}")
        elif merged[name] and not held_issues:
            # a merged change is news only once its worker has nothing left to do, since until then the worker goes on with its next task
            lines.append(f"merged {' '.join(f'#{number}' for number in merged[name])} by {name}: it holds nothing open; close it and clean its worktree")
        elif status[name] in ("idle", "done") and role(name) != "sentinel" and (not held_issues or any(stalled(issue, open_issues) for issue in held_issues)) \
                and not background(by_name[name]):
            # a sentinel waits idle between the rounds of its duty; a worker whose tasks all wait on a task, the owner or the manager has nothing to do yet
            lines.append(f"idle {name}: holds {held}; give it its next step, answer what it waits on, or close it when it holds nothing open")
    news = {}
    own = own_reports.urls()  # what this manager posted itself is no news to it
    for issue, comment in data.get("feed", []):
        if fed_urls is not None and comment["url"] not in fed_urls and comment["url"] not in own:
            fed_urls.add(comment["url"])
            news.setdefault(issue["number"], (issue, []))[1].append(comment)
    for issue, posted in news.values():
        said = " | ".join(comment["body"].strip().splitlines()[0] for comment in posted)
        # a push reaches the owner away only through Remote Control, so without it the line sends none
        push = "push it to the owner by PushNotification" if remote_control.active((me.get("agent_session") or {}).get("value")) else "tell the owner in your tab; send no push, since Remote Control is off in your session"
        lines.append(f"feed #{issue['number']} {issue_state.title(issue)}: {said} ({posted[-1]['url']}); {push}")
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
    """Each held issue's state from a fresh read, since a list read can lag a comment just posted."""
    held = [issue for issue in issues() or [] if holds(issue, me["name"])]
    fresh = [board.fresh(issue["number"]) or issue for issue in held]
    return [f"#{issue['number']} {issue_state.title(issue)} ({issue['url']}): " + ("waits on your manager" if asking(issue) else "open") for issue in fresh]


def worker_read(me):
    """What a worker's wait needs from the board, read once and kept by the caller until something changed; None when a read failed."""
    found = issues()
    pulls = landing.pulls("open")
    if found is None or pulls is None:
        return None
    for pull in (pull for pull in pulls if owns(me["name"], pull["headRefName"])):  # the list read lacks mergeability, which a pull read gives
        pull["mergeable"] = {True: "CONFLICTING", False: "MERGEABLE"}.get(landing.conflicts(pull["number"]))
    blockers = {issue["number"]: board.blockers(issue["number"]) for issue in found if holds(issue, me["name"])}
    return None if None in blockers.values() else {"found": found, "prs": pulls, "blockers": blockers}


def worker_actions(me, waiting, data=None):
    """What ended a wait of this worker, as the act it needs; None when a read failed. WAITING, kept by the caller
    across polls, holds the held issues last seen with an open blocker, so only the closing of the last one prints.
    DATA is a `worker_read` kept from an earlier poll, else a read now."""
    data = data or worker_read(me)
    if data is None:
        return None
    name, found, pulls = me["name"], data["found"], data["prs"]
    lines = limited(found, ISSUE_LIMIT, "open-issue")
    for issue in (issue for issue in found if holds(issue, name)):
        latest = issue_state.questions(issue)[-1:]
        if latest and latest[0]["answer"]:
            lines.append(f"answered #{issue['number']}: {latest[0]['answer']['url']} answers your {ASK}:; act on it")
        if data["blockers"][issue["number"]]:
            waiting.add(issue["number"])
        elif issue["number"] in waiting:
            waiting.discard(issue["number"])
            lines.append(f"start #{issue['number']}: every issue it waited on is closed")
    for pull in pulls:
        if owns(name, pull["headRefName"]) and pull.get("mergeable") == "CONFLICTING":
            lines.append(f"rebase #{pull['number']}: it conflicts with its base")
    return lines

"""Each role's next actions: the gaps between the board's issues and the live team, as lines a monitor or hook prints."""
import os

import board
import issue_state
import landing
import team_settings
from session import screen, tabs
from team_names import crowding, members, owns, project, role

ISSUE_LIMIT, PULL_LIMIT = 200, 50

ASK, ANSWER = issue_state.WORD["ask"], issue_state.WORD["answer"]
FEED = next(word for word, meaning in issue_state.KEYWORDS.items() if not meaning)  # the keyword that only informs, which the owner reads as what happened


def issues(project=None, state="open"):
    found = board.issues(state, project)
    return found and found[:ISSUE_LIMIT]


def limited(found, limit, what):
    """A line when a list came back full, since the read then drops the rest without a word."""
    return [f"limit: the {what} list returned its limit of {limit}, so some are not shown"] if len(found) >= limit else []


def holds(issue, name):
    return name in (issue_state.compose(issue)["holders"] or [])


def asking(issue):
    return [kind for kind, _, _ in issue_state.exchange(issue)][-1:] == ["ask"]


def unanswered(issue):
    """An outside contributor's issue or pull request that no trusted record has routed or left for later yet."""
    return not issue_state.trusted(issue) and not issue_state.deferral(issue) and not issue_state.holder_values(issue)


def feed_read(name, since):
    """The trusted reports posted since SINCE (an ISO time) on this manager's project's backlogs and on its issues closed now, as (issue, comment);
    None when a read failed. A task's other reports, such as each precheck table, are steps the owner need not follow."""
    touched = board.issues("all", project(name), comments=False, since=since)
    posted = board.comments_since(since)
    if touched is None or posted is None:
        return None
    backlog = team_settings.load(os.getcwd())["backlog_label"]
    by = {issue["number"]: issue for issue in touched if issue["state"] == "CLOSED" or backlog in issue["labels"]}
    # `since` matches an edit too, so an old comment edited now is left out by its creation time
    found = [(by[number], comment) for number, comment in posted
             if number in by and comment["createdAt"] >= since and issue_state.trusted(comment) and issue_state.keyword(comment["body"]) == FEED]
    # a closed task's last report is its close summary
    last = {issue["number"]: comment["url"] for issue, comment in found}
    return [(issue, comment) for issue, comment in found if issue["state"] == "OPEN" or last[issue["number"]] == comment["url"]]


def manager_read(me, history=False, since=None):
    """What a manager's gaps need from the board, read once and kept by the caller until something changed; None when a read failed.
    HISTORY adds whether a worker ever held a closed issue, for a manager that has not yet seen one; SINCE adds the reports posted since then."""
    found = issues(project(me["name"]))
    # a worker may hold an open issue the scope label misses, which the idle line must still count
    everything = issues() if found is not None and board.scoped(project(me["name"])) else found
    # one page of the latest updated closed pulls, whose merged ones are the newest merges
    pulls = landing.pulls("closed", limit=PULL_LIMIT)
    pulls = pulls and [pull for pull in pulls if pull["mergedAt"]]
    # an outside contributor's issue or pull request carries no scope label, so it is read across the repository
    outside = board.issues(pulls=True, comments=False)
    outside = outside and [board.fresh(issue["number"]) for issue in outside if not issue_state.trusted(issue)]
    feed = feed_read(me["name"], since) if since else []  # a first read has no earlier one, so a restart pushes nothing old
    if found is None or everything is None or pulls is None or outside is None or None in outside or feed is None:
        return None
    return {"found": found, "everything": everything, "prs": pulls, "outside": [issue for issue in outside if unanswered(issue)],
            "had_worker": had_worker(me) if history else False, "feed": feed}


def manager_actions(me, listed, data=None, fed_urls=None):
    """A manager's gaps from DATA, a `manager_read` kept from an earlier poll, else from a read now. FED_URLS, kept by the caller
    across polls, holds the urls of the reports already fed, since two reads overlap by the clock skew."""
    data = data or manager_read(me)
    if data is None:
        return None
    team = members(me, listed)
    status = {agent.get("name"): agent.get("agent_status") for agent in listed}
    panes = {agent.get("name"): agent.get("pane_id") for agent in listed}
    found, pulls = data["found"], data["prs"]
    lines = limited(found, ISSUE_LIMIT, "open-issue")  # merged PRs past the newest are always many and no live worker's
    if crowd := crowding(me, listed):
        lines.append(f"shared workspace: {', '.join(crowd)} manage another project in your workspace; move to a workspace of your own: "
                     f"`start` `{me['name']}-next` with `succeed {me['name']}`, as Succession says, which opens one")
    # a started worker names its tab before its agent is live, so its tab counts it as routed
    present = set(team) | {tab.get("label") for tab in tabs(me.get("workspace_id", ""))}
    # a cloud name holds on every open issue, so a task its worker filed itself counts as held though only the backlog names it cloud
    present |= {name for issue in data["everything"] for name in issue_state.cloud(issue)}
    for issue in found:
        if not unanswered(issue) and not issue_state.deferral(issue) and not any(holds(issue, name) for name in present if name):
            lines.append(f"route #{issue['number']} {issue_state.title(issue)}: no live worker holds it; route it, or leave it for later by a {ANSWER}: with an empty holders and a deferred reason")
        if asking(issue):
            lines.append(f"answer #{issue['number']}: its worker asks; post your {ANSWER}: there; the worker waits on it")
    for issue in data["outside"]:
        if issue.get("isPullRequest"):
            lines.append(f"outside #{issue['number']} {issue_state.title(issue)}: an outside contributor opened this pull request; close it unread with a comment that outside pull requests are not accepted and issues are welcome")
        else:
            lines.append(f"outside #{issue['number']} {issue_state.title(issue)}: an outside contributor opened it; ask the owner, then route it or leave it for later by a {ANSWER}: with an empty holders and a deferred reason")
    for name in team:
        held = " ".join(f"#{issue['number']}" for issue in data["everything"] if holds(issue, name)) or "nothing open"
        if status[name] == "blocked":
            lines.append(f"blocked {name} (pane {panes[name]}): it waits at a tool-use prompt; tell the owner this screen, then answer by the Tool prompt rule once the owner says so: {prompt_text(panes[name])}")
        elif status[name] in ("idle", "done") and role(name) != "sentinel":  # a sentinel waits idle between the rounds of its duty
            lines.append(f"idle {name}: holds {held}; it needs what waits, or close it when it holds nothing open")
    for pull, name in ((pull, name) for pull in pulls for name in team if owns(name, pull["headRefName"])):
        lines.append(f"merged #{pull['number']} by {name}: once {name} holds nothing open, close it and clean its worktree")
    news = {}
    for issue, comment in data.get("feed", []):
        if fed_urls is not None and comment["url"] not in fed_urls:
            fed_urls.add(comment["url"])
            news.setdefault(issue["number"], (issue, []))[1].append(comment)
    for issue, posted in news.values():
        said = " | ".join(comment["body"].strip().splitlines()[0] for comment in posted)
        lines.append(f"feed #{issue['number']} {issue_state.title(issue)}: {said} ({posted[-1]['url']}); push it to the owner by PushNotification")
    return lines


def prompt_text(pane):
    """The last lines of a blocked pane's screen, which hold the prompt's question and numbered choices, on one line."""
    lines = [line.strip() for line in screen(pane).splitlines() if line.strip()]
    return " | ".join(lines[-8:])


def had_worker(me):
    """Whether a manager of this project ever routed a worker, read from the holders of its closed issues, so a restarted monitor knows what its memory lost."""
    found = issues(project(me["name"]), "closed")
    return any(role(name) == "worker" for issue in found or [] for names in issue_state.holder_values(issue) for name in names)


def exit_action(me, listed):
    """The exit line, or None for the keeper, the live manager first by name, who stays so one manager is always live:
    two managers that each answer the other's proposal would otherwise both close."""
    managers = sorted({agent["name"] for agent in listed if role(agent.get("name")) == "manager"} | {me["name"]})
    others = [name for name in managers if name != me["name"]]
    return f"exit: no worker is live and nothing waits; propose your exit to {', '.join(others)} as step 5 says" if managers[0] != me["name"] else None


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
        turns = issue_state.exchange(issue)
        if [kind for kind, _, _ in turns[-2:]] == ["ask", "answer"]:
            lines.append(f"answered #{issue['number']}: {turns[-1][2]['url']} answers your {ASK}:; act on it")
        if data["blockers"][issue["number"]]:
            waiting.add(issue["number"])
        elif issue["number"] in waiting:
            waiting.discard(issue["number"])
            lines.append(f"start #{issue['number']}: every issue it waited on is closed")
    for pull in pulls:
        if owns(name, pull["headRefName"]) and pull.get("mergeable") == "CONFLICTING":
            lines.append(f"rebase #{pull['number']}: it conflicts with its base")
    return lines

"""Each role's next actions: the gaps between the board's issues and the live team, as lines a monitor or hook prints."""
import board
import issue_state
import landing
from herdr_agents import members, owns, project, role, screen, tabs

ISSUE_LIMIT, PR_LIMIT = 200, 50

ASK, ANSWER = issue_state.WORD["ask"], issue_state.WORD["answer"]
FEED = next(w for w, r in issue_state.KEYWORDS.items() if not r)  # the keyword that only informs, which the owner reads as what happened


def issues(project=None, state="open"):
    found = board.issues(state, project)
    return found and found[:ISSUE_LIMIT]


def limited(found, limit, what):
    """A line when a list came back full, since the read then drops the rest without a word."""
    return [f"limit: the {what} list returned its limit of {limit}, so some are not shown"] if len(found) >= limit else []


def holds(issue, name):
    return name in (issue_state.compose(issue)["holders"] or [])


def asking(issue):
    return [r for r, _, _ in issue_state.exchange(issue)][-1:] == ["ask"]


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
    by = {i["number"]: i for i in touched if i["state"] == "CLOSED" or "backlog" in i["labels"]}
    # `since` matches an edit too, so an old comment edited now is left out by its creation time
    found = [(by[n], c) for n, c in posted
             if n in by and c["createdAt"] >= since and issue_state.trusted(c) and issue_state.keyword(c["body"]) == FEED]
    # a closed task's last report is its close summary
    last = {i["number"]: c["url"] for i, c in found}
    return [(i, c) for i, c in found if i["state"] == "OPEN" or last[i["number"]] == c["url"]]


def manager_read(me, history=False, since=None):
    """What a manager's gaps need from the board, read once and kept by the caller until something changed; None when a read failed.
    HISTORY adds whether a worker ever held a closed issue, for a manager that has not yet seen one; SINCE adds the reports posted since then."""
    found = issues(project(me["name"]))
    # a worker may hold an open issue the scope label misses, which the idle line must still count
    everything = issues() if found is not None and board.scoped(project(me["name"])) else found
    # one page of the latest updated closed pulls, whose merged ones are the newest merges
    prs = landing.pulls("closed", limit=PR_LIMIT)
    prs = prs and [p for p in prs if p["mergedAt"]]
    # an outside contributor's issue or pull request carries no scope label, so it is read across the repository
    outside = board.issues(pulls=True, comments=False)
    outside = outside and [board.fresh(i["number"]) for i in outside if not issue_state.trusted(i)]
    feed = feed_read(me["name"], since) if since else []  # a first read has no earlier one, so a restart pushes nothing old
    if found is None or everything is None or prs is None or outside is None or None in outside or feed is None:
        return None
    return {"found": found, "everything": everything, "prs": prs, "outside": [i for i in outside if unanswered(i)],
            "had_worker": had_worker(me) if history else False, "feed": feed}


def manager_actions(me, listed, data=None, fed=None):
    """A manager's gaps from DATA, a `manager_read` kept from an earlier poll, else from a read now. FED, kept by the caller
    across polls, holds the urls of the reports already fed, since two reads overlap by the clock skew."""
    data = data or manager_read(me)
    if data is None:
        return None
    team = members(me, listed)
    status = {a.get("name"): a.get("agent_status") for a in listed}
    panes = {a.get("name"): a.get("pane_id") for a in listed}
    found, prs = data["found"], data["prs"]
    lines = limited(found, ISSUE_LIMIT, "open-issue")  # merged PRs past the newest are always many and no live worker's
    # a started worker names its tab before its agent is live, so its tab counts it as routed
    present = set(team) | {t.get("label") for t in tabs(me.get("workspace_id", ""))}
    for i in found:
        if not unanswered(i) and not issue_state.deferral(i) and not any(holds(i, n) for n in present if n):
            lines.append(f"route #{i['number']} {i['title']}: no live worker holds it; route it, or leave it for later by a {ANSWER}: with an empty holders and a deferred reason")
        if asking(i):
            lines.append(f"answer #{i['number']}: its worker asks; post your {ANSWER}: there; the worker waits on it")
    for i in data["outside"]:
        lines.append(f"outside #{i['number']} {i['title']}: an outside contributor opened it; ask the owner, then route it or leave it for later by a {ANSWER}: with an empty holders and a deferred reason")
    for n in team:
        held = " ".join(f"#{i['number']}" for i in data["everything"] if holds(i, n)) or "nothing open"
        if status[n] == "blocked":
            lines.append(f"blocked {n} (pane {panes[n]}): it waits at a tool-use prompt; tell the owner this screen, then answer by the Tool prompt rule once the owner says so: {prompt_text(panes[n])}")
        elif status[n] in ("idle", "done"):
            lines.append(f"idle {n}: holds {held}; it needs what waits, or close it when it holds nothing open")
    for p, n in ((p, n) for p in prs for n in team if owns(n, p["headRefName"])):
        lines.append(f"merged #{p['number']} by {n}: once {n} holds nothing open, close it and clean its worktree")
    news = {}
    for i, c in data.get("feed", []):
        if fed is not None and c["url"] not in fed:
            fed.add(c["url"])
            news.setdefault(i["number"], (i, []))[1].append(c)
    for i, posted in news.values():
        said = " | ".join(c["body"].strip().splitlines()[0] for c in posted)
        lines.append(f"feed #{i['number']} {i['title']}: {said} ({posted[-1]['url']}); push it to the owner by PushNotification")
    return lines


def prompt_text(pane):
    """The last lines of a blocked pane's screen, which hold the prompt's question and numbered choices, on one line."""
    lines = [l.strip() for l in screen(pane).splitlines() if l.strip()]
    return " | ".join(lines[-8:])


def had_worker(me):
    """Whether a manager of this project ever routed a worker, read from the holders of its closed issues, so a restarted monitor knows what its memory lost."""
    found = issues(project(me["name"]), "closed")
    return any(role(n) == "worker" for i in found or [] for names in issue_state.holder_values(i) for n in names)


def exit_action(me, listed):
    """The exit line, or None for the only live manager, who stays since no other can answer its proposal."""
    others = [a["name"] for a in listed if a is not me and role(a.get("name")) == "manager"]
    return f"exit: no worker is live and nothing waits; propose your exit to {', '.join(others)} as step 5 says" if others else None


def worker_goal(me):
    """Each held issue's state from a fresh read, since a list read can lag a comment just posted."""
    held = [i for i in issues() or [] if holds(i, me["name"])]
    fresh = [board.fresh(i["number"]) or i for i in held]
    return [f"#{i['number']} {i['title']} ({i['url']}): " + ("waits on your manager" if asking(i) else "open") for i in fresh]


def worker_read(me):
    """What a worker's wait needs from the board, read once and kept by the caller until something changed; None when a read failed."""
    found = issues()
    prs = landing.pulls("open")
    if found is None or prs is None:
        return None
    for p in (p for p in prs if owns(me["name"], p["headRefName"])):  # the list read lacks mergeability, which a pull read gives
        p["mergeable"] = {True: "CONFLICTING", False: "MERGEABLE"}.get(landing.conflicts(p["number"]))
    blockers = {i["number"]: board.blockers(i["number"]) for i in found if holds(i, me["name"])}
    return None if None in blockers.values() else {"found": found, "prs": prs, "blockers": blockers}


def worker_actions(me, waiting, data=None):
    """What ended a wait of this worker, as the act it needs; None when a read failed. WAITING, kept by the caller
    across polls, holds the held issues last seen with an open blocker, so only the closing of the last one prints.
    DATA is a `worker_read` kept from an earlier poll, else a read now."""
    data = data or worker_read(me)
    if data is None:
        return None
    name, found, prs = me["name"], data["found"], data["prs"]
    lines = limited(found, ISSUE_LIMIT, "open-issue")
    for i in (i for i in found if holds(i, name)):
        turns = issue_state.exchange(i)
        if [r for r, _, _ in turns[-2:]] == ["ask", "answer"]:
            lines.append(f"answered #{i['number']}: {turns[-1][2]['url']} answers your {ASK}:; act on it")
        if data["blockers"][i["number"]]:
            waiting.add(i["number"])
        elif i["number"] in waiting:
            waiting.discard(i["number"])
            lines.append(f"start #{i['number']}: every issue it waited on is closed")
    for p in prs:
        if owns(name, p["headRefName"]) and p.get("mergeable") == "CONFLICTING":
            lines.append(f"rebase #{p['number']}: it conflicts with its base")
    return lines

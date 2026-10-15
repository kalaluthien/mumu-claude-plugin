"""Each role's next actions: the gaps between GitHub's issues and the live team, as lines a monitor or hook prints."""
import issue_state
from github_issues import ISSUE_LIMIT, PR_LIMIT, issues, limited
from herdr_agents import members, owns, project, role, tabs
from json_command import run

ASK, ANSWER = issue_state.WORD["ask"], issue_state.WORD["answer"]


def holds(issue, name):
    return name in (issue_state.compose(issue)["holders"] or [])


def asking(issue):
    return [r for r, _, _ in issue_state.exchange(issue)][-1:] == ["ask"]


def manager_actions(me, listed):
    team = members(me, listed)
    status = {a.get("name"): a.get("agent_status") for a in listed}
    found = issues(project(me["name"]))
    prs = run("gh", "pr", "list", "--state", "merged", "--limit", str(PR_LIMIT), "--json", "number,headRefName")
    if found is None or prs is None:
        return None
    lines = limited(found, ISSUE_LIMIT, "open-issue")  # merged PRs past the newest are always many and no live worker's
    # a started worker names its tab before its agent is live, so its tab counts it as routed
    present = set(team) | {t.get("label") for t in tabs(me.get("workspace_id", ""))}
    for i in found:
        deferred = issue_state.compose(i)["holders"] == []  # holders set empty records a decision to leave it for later
        if not deferred and not any(holds(i, n) for n in present if n):
            lines.append(f"route #{i['number']} {i['title']}: no live worker holds it; route it, or leave it for later by a {ANSWER}: with an empty holders")
        if asking(i):
            lines.append(f"answer #{i['number']}: its worker asks; post your {ANSWER}: there; the worker waits on it")
    for n in team:
        held = " ".join(f"#{i['number']}" for i in found if holds(i, n)) or "nothing open"
        if status[n] == "blocked":
            lines.append(f"blocked {n}: it waits at a tool-use prompt; the owner needs its tab")
        elif status[n] in ("idle", "done"):
            lines.append(f"idle {n}: holds {held}; it needs what waits, or close it when it holds nothing open")
    for p, n in ((p, n) for p in prs for n in team if owns(n, p["headRefName"])):
        lines.append(f"merged #{p['number']} by {n}: once {n} holds nothing open, close it and clean its worktree")
    return lines


def had_worker(me):
    """Whether a manager of this project ever routed a worker, read from the holders of its closed issues, so a restarted monitor knows what its memory lost."""
    found = issues(project(me["name"]), "closed")
    return any(role(n) == "worker" for i in found or [] for names in issue_state.holder_values(i) for n in names)


def exit_action(me, listed):
    others = [a["name"] for a in listed if a is not me and role(a.get("name")) == "manager"]
    return ("exit: no worker is live and nothing waits; " + (f"propose your exit to {', '.join(others)} as step 5 says" if others
            else "you are the only live manager, so stay and /compact as step 5 says"))


def worker_goal(me):
    """Each held issue's state from a fresh read, since `gh issue list` can lag a comment just posted."""
    held = [i for i in issues() or [] if holds(i, me["name"])]
    fresh = [run("gh", "issue", "view", i["url"], "--json", "number,title,url,body,comments") or i for i in held]
    return [f"#{i['number']} {i['title']} ({i['url']}): " + ("waits on your manager" if asking(i) else "open") for i in fresh]


def worker_actions(me, waiting):
    """What ended a wait of this worker, as the act it needs; None when a read failed. WAITING, kept by the caller
    across polls, holds the held issues last seen with an open blocker, so only the closing of the last one prints."""
    name, found = me["name"], issues()
    prs = run("gh", "pr", "list", "--state", "open", "--json", "number,headRefName,mergeable")
    if found is None or prs is None:
        return None
    lines = limited(found, ISSUE_LIMIT, "open-issue")
    for i in (i for i in found if holds(i, name)):
        turns = issue_state.exchange(i)
        if [r for r, _, _ in turns[-2:]] == ["ask", "answer"]:
            lines.append(f"answered #{i['number']}: {turns[-1][2]['url']} answers your {ASK}:; act on it")
        blockers = run("gh", "api", f"repos/{{owner}}/{{repo}}/issues/{i['number']}/dependencies/blocked_by", "--jq", "[.[].state]")
        if blockers is None:
            return None
        if "open" in blockers:
            waiting.add(i["number"])
        elif i["number"] in waiting:
            waiting.discard(i["number"])
            lines.append(f"start #{i['number']}: every issue it waited on is closed")
    for p in prs:
        if owns(name, p["headRefName"]) and p["mergeable"] == "CONFLICTING":
            lines.append(f"rebase #{p['number']}: it conflicts with the default branch")
    return lines

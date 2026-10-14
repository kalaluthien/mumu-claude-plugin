import json
import os
import re
import subprocess

ISSUE_LIMIT, PR_LIMIT = 200, 50


def run(*argv):
    """The command's parsed JSON output, or None when it fails or is missing, such as herdr outside a multiplexer."""
    try:
        p = subprocess.run(argv, capture_output=True, text=True)
        return json.loads(p.stdout) if p.returncode == 0 and p.stdout.strip() else None
    except (OSError, ValueError):
        return None


def sessions(session_id=None):
    """Every live agent, and this session's own: its pane's, unless the pane runs another session, as a worker's child does."""
    listed = (run("herdr", "agent", "list") or {}).get("result", {}).get("agents", [])
    me = next((a for a in listed if a.get("pane_id") == os.environ.get("HERDR_PANE_ID")), {})
    own = not session_id or (me.get("agent_session") or {}).get("value") in (None, "", session_id)
    return listed, me if own else {}


def agent(name):
    return next((a for a in sessions()[0] if a.get("name") == name), None)


def screen(pane):
    return subprocess.run(["herdr", "agent", "read", pane, "--source", "visible"], capture_output=True, text=True).stdout


def issues(project=None, state="open"):
    scoped = project and f"scope:{project}" in [x["name"] for x in run("gh", "label", "list", "--search", "scope:", "--json", "name") or []]
    return run("gh", "issue", "list", "--state", state, "--limit", str(ISSUE_LIMIT), "--json", "number,title,body,comments,url",
               *(["--label", f"scope:{project}"] if scoped else []))


def holds(issue, name):
    """Only a claim names a holder: a `DECIDED: <name> holds` comment or a `held by <name>` line, never a passing mention."""
    n = re.escape(name)
    texts = [issue["body"], *(c["body"] for c in issue["comments"])]
    return any(c["body"].lstrip().startswith("DECIDED:") and re.search(rf"(?<![\w-])`?{n}`?\s+holds\b", c["body"])
               for c in issue["comments"]) or any(
        re.search(rf"\bheld by `?{n}(?![\w-])", t) for t in texts)


def limited(found, limit, what):
    """A line when a list came back full, since gh then drops the rest without a word."""
    return [f"limit: the {what} list returned its limit of {limit}, so some are not shown"] if len(found) >= limit else []


def records(issue):
    """Its BLOCKED: and DECIDED: comments, oldest first, each as (kind, comment)."""
    return [(r, c) for c in issue["comments"] if (r := c["body"].lstrip()[:8].upper()) in ("BLOCKED:", "DECIDED:")]


def asking(issue):
    return [r for r, _ in records(issue)][-1:] == ["BLOCKED:"]


def members(me, listed):
    return [a["name"] for a in listed if a.get("workspace_id") == me.get("workspace_id") and a is not me and a.get("name")]


def manager_actions(me, listed):
    team = members(me, listed)
    status = {a.get("name"): a.get("agent_status") for a in listed}
    found = issues(me["name"].removesuffix("-manager"))
    prs = run("gh", "pr", "list", "--state", "merged", "--limit", str(PR_LIMIT), "--json", "number,headRefName")
    if found is None or prs is None:
        return None
    lines = limited(found, ISSUE_LIMIT, "open-issue") + limited(prs, PR_LIMIT, "merged-PR")
    # a started worker names its tab before its agent is live, so its tab counts it as routed
    tabs = (run("herdr", "tab", "list", "--workspace", me.get("workspace_id", "")) or {}).get("result", {}).get("tabs", [])
    present = set(team) | {t.get("label") for t in tabs}
    for i in found:
        if not any(holds(i, n) for n in present if n):
            lines.append(f"route #{i['number']} {i['title']}: no live worker holds it; route it, or leave it for later")
        if asking(i):
            lines.append(f"answer #{i['number']}: its worker asks; post your DECIDED: there; the worker waits on it")
    for n in team:
        held = " ".join(f"#{i['number']}" for i in found if holds(i, n)) or "nothing open"
        if status[n] == "blocked":
            lines.append(f"blocked {n}: it waits at a tool-use prompt; the owner needs its tab")
        elif status[n] in ("idle", "done"):
            lines.append(f"idle {n}: holds {held}; it needs what waits, or close it when it holds nothing open")
    for p, n in ((p, n) for p in prs for n in team if p["headRefName"] == n or p["headRefName"].startswith(n + "-")):
        lines.append(f"merged #{p['number']} by {n}: once {n} holds nothing open, close it and clean its worktree")
    return lines


def had_worker(me):
    """Whether a manager of this project ever routed a worker, read from the `DECIDED: <name>-worker holds` comments of its closed issues, so a restarted monitor knows what its memory lost."""
    found = issues(me["name"].removesuffix("-manager"), "closed")
    return any(re.match(r"\s*DECIDED:\s*`?[\w-]+-worker`?\s+holds\b", c["body"]) for i in found or [] for c in i["comments"])


def exit_action(me, listed):
    others = [a["name"] for a in listed if a is not me and a.get("name", "").endswith("-manager")]
    return ("exit: no worker is live and nothing waits; " + (f"propose your exit to {', '.join(others)} as step 5 says" if others
            else "you are the only live manager, so stay and /compact as step 5 says"))


def worker_goal(me):
    """Each held issue's state from a fresh read, since `gh issue list` can lag a comment just posted."""
    held = [i for i in issues() or [] if holds(i, me["name"])]
    fresh = [run("gh", "issue", "view", i["url"], "--json", "number,title,url,body,comments") or i for i in held]
    return [f"#{i['number']} {i['title']} ({i['url']}): " + ("waits on your manager" if asking(i) else "open") for i in fresh]


# what a tool's result says when it starts background work, by tool
STARTED = {"Agent": r"^agentId: (\w+)", "SendMessage": r"\"resumedAgentId\":\s*\"(\w+)\"", "Bash": r"\ACommand running in background with ID: (\w+)"}


def text(content):
    return content if isinstance(content, str) else " ".join(x.get("text", "") for x in content or [] if isinstance(x, dict))


def running_work(transcript):
    """Ids of the background agents and commands a transcript started that no task notification has ended yet."""
    running, tools = set(), {}
    try:
        records = [json.loads(line) for line in open(transcript) if line.strip()]
    except (OSError, ValueError):
        return running
    for r in records:
        content = r.get("content") if r.get("type") == "queue-operation" else (r.get("message") or {}).get("content")
        if isinstance(content, str):  # a notification arrives as plain text, never inside a tool result
            running.difference_update(re.findall(r"<task-id>(\w+)</task-id>.*?<status>(?:completed|failed|killed|stopped)</status>", content, re.S))
            continue
        for b in (b for b in content or [] if isinstance(b, dict)):
            if b.get("type") == "tool_use":
                tools[b.get("id")] = STARTED.get(b.get("name"))
                running.discard((b.get("input") or {}).get("task_id") if b.get("name") == "TaskStop" else None)
            elif (pattern := tools.get(b.get("tool_use_id"))) and (found := re.search(pattern, text(b.get("content")), re.M)):
                running.add(found.group(1))
    return running


def worker_actions(me, waiting):
    """What ended a wait of this worker, as the act it needs; None when a read failed. WAITING, kept by the caller
    across polls, holds the held issues last seen with an open blocker, so only the closing of the last one prints."""
    name, found = me["name"], issues()
    prs = run("gh", "pr", "list", "--state", "open", "--json", "number,headRefName,mergeable")
    if found is None or prs is None:
        return None
    lines = limited(found, ISSUE_LIMIT, "open-issue")
    for i in (i for i in found if holds(i, name)):
        kinds = records(i)
        if [r for r, _ in kinds[-2:]] == ["BLOCKED:", "DECIDED:"]:
            lines.append(f"answered #{i['number']}: {kinds[-1][1]['url']} answers your BLOCKED:; act on it")
        blockers = run("gh", "api", f"repos/{{owner}}/{{repo}}/issues/{i['number']}/dependencies/blocked_by", "--jq", "[.[].state]")
        if blockers is None:
            return None
        if "open" in blockers:
            waiting.add(i["number"])
        elif i["number"] in waiting:
            waiting.discard(i["number"])
            lines.append(f"start #{i['number']}: every issue it waited on is closed")
    for p in prs:
        if (p["headRefName"] == name or p["headRefName"].startswith(name + "-")) and p["mergeable"] == "CONFLICTING":
            lines.append(f"rebase #{p['number']}: it conflicts with the default branch")
    return lines

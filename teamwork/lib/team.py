import json
import os
import re
import subprocess


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


def issues(project=None):
    scoped = project and f"scope:{project}" in [x["name"] for x in run("gh", "label", "list", "--search", "scope:", "--json", "name") or []]
    return run("gh", "issue", "list", "--state", "open", "--limit", "200", "--json", "number,title,body,comments,url",
               *(["--label", f"scope:{project}"] if scoped else []))


def holds(issue, name):
    text = " ".join([issue["body"], *(c["body"] for c in issue["comments"])])
    return re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text) is not None


def asking(issue):
    records = [r for c in issue["comments"] if (r := c["body"].lstrip()[:8].upper()) in ("BLOCKED:", "DECIDED:")]
    return records[-1:] == ["BLOCKED:"]


def manager_actions(me, listed):
    team = [a["name"] for a in listed if a.get("workspace_id") == me.get("workspace_id") and a is not me and a.get("name")]
    status = {a.get("name"): a.get("agent_status") for a in listed}
    found, lines = issues(me["name"].removesuffix("-manager")), []
    prs = run("gh", "pr", "list", "--state", "merged", "--limit", "50", "--json", "number,headRefName")
    if found is None or prs is None:
        return None
    for i in found:
        if not any(holds(i, n) for n in team):
            lines.append(f"route #{i['number']} {i['title']}: no live worker holds it; route it, or leave it for later")
        if asking(i):
            lines.append(f"answer #{i['number']}: its worker asks; post your DECIDED: there, then tell the worker")
    for n in team:
        held = " ".join(f"#{i['number']}" for i in found if holds(i, n)) or "nothing open"
        if status[n] == "blocked":
            lines.append(f"blocked {n}: it waits at a tool-use prompt; give the owner its tab")
        elif status[n] in ("idle", "done"):
            lines.append(f"idle {n}: holds {held}; tell it what waits, or close it when it holds nothing open")
    for p, n in ((p, n) for p in prs for n in team if p["headRefName"] == n or p["headRefName"].startswith(n + "-")):
        lines.append(f"merged #{p['number']} by {n}: once {n} holds nothing open, close it and clean its worktree")
    return lines


def worker_goal(me):
    return [f"#{i['number']} {i['title']} ({i['url']}): " + ("waits on your manager" if asking(i) else "open")
            for i in issues() or [] if holds(i, me["name"])]

"""Reads a project's issues from GitHub."""
from json_command import run

ISSUE_LIMIT, PR_LIMIT = 200, 50


def issues(project=None, state="open"):
    scoped = project and f"scope:{project}" in [x["name"] for x in run("gh", "label", "list", "--search", "scope:", "--json", "name") or []]
    return run("gh", "issue", "list", "--state", state, "--limit", str(ISSUE_LIMIT), "--json", "number,title,body,comments,url",
               *(["--label", f"scope:{project}"] if scoped else []))


def limited(found, limit, what):
    """A line when a list came back full, since gh then drops the rest without a word."""
    return [f"limit: the {what} list returned its limit of {limit}, so some are not shown"] if len(found) >= limit else []

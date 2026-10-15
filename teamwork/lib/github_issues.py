"""Reads a project's issues from GitHub."""
from json_command import run

ISSUE_LIMIT, PR_LIMIT = 200, 50


def scope_label(project):
    label = f"scope:{project}"
    # gh prints nothing, not `[]`, when no label matches, so an empty read is a repository without that label
    return label if label in [x["name"] for x in run("gh", "label", "list", "--search", label, "--json", "name") or []] else None


def issues(project=None, state="open"):
    label = project and scope_label(project)
    return run("gh", "issue", "list", "--state", state, "--limit", str(ISSUE_LIMIT), "--json", "number,title,body,comments,url",
               *(["--label", label] if label else []))


def limited(found, limit, what):
    """A line when a list came back full, since gh then drops the rest without a word."""
    return [f"limit: the {what} list returned its limit of {limit}, so some are not shown"] if len(found) >= limit else []

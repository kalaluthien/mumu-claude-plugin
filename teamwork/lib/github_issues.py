"""Reads a project's issues from GitHub."""
from json_command import run

ISSUE_LIMIT, PR_LIMIT = 200, 50


def scope_label(project):
    label = f"scope:{project}"
    # a REST read, which costs no GraphQL point; a missing label answers 404, which `run` reads as None
    return label if run("gh", "api", f"repos/{{owner}}/{{repo}}/labels/{label.replace(':', '%3A')}", "--jq", "{name}") else None


def issues(project=None, state="open"):
    label = project and scope_label(project)
    return run("gh", "issue", "list", "--state", state, "--limit", str(ISSUE_LIMIT), "--json", "number,title,body,comments,url",
               *(["--label", label] if label else []))


def limited(found, limit, what):
    """A line when a list came back full, since gh then drops the rest without a word."""
    return [f"limit: the {what} list returned its limit of {limit}, so some are not shown"] if len(found) >= limit else []

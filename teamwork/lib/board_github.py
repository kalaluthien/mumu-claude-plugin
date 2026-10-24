"""The board on GitHub: issues and comments read by REST, which spends no GraphQL point, the issue pane's tree by GraphQL, and writes by `gh api`."""
import functools
import hashlib
import itertools
import json
import os
import re
import subprocess
from urllib.parse import quote

import claude_config
from issue_board import SHOWN_CLOSED
from json_command import need, run
import team_settings

TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}
CACHE = claude_config.folder() / "teamwork" / "github-cache"
SINCE = re.compile(r"(?<=since=)[^&]*")
# one point or two per read: GitHub charges each connection a node is asked for, so the sub-issues' blockers, the costliest part,
# are read only for the closed ones the board shows, by the second query
ISSUES = """query($owner: String!, $name: String!, $labels: [String!], $after: String) {
  repository(owner: $owner, name: $name) {
    issues(states: OPEN, first: 30, after: $after, labels: $labels, orderBy: {field: CREATED_AT, direction: ASC}) {
      nodes { number title url body authorAssociation parent { number } labels(first: 20) { nodes { name } } subIssuesSummary { total completed }
              subIssues(last: 50) { nodes { number title url state stateReason authorAssociation } }
              blockedBy(first: 20) { nodes { number state } } comments(last: 100) { nodes { body url authorAssociation } } }
      pageInfo { hasNextPage endCursor } } } }"""
BLOCKERS = """query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    %s } }"""
# only where a command segment starts, so gh text quoted inside another command's argument is not read as a call
GH_TEXT = re.compile(r"(?:^|&&|\|\||[;|(`\n]|\b(?:then|do|else)\s)\s*(?:\w+=\S*\s+)*(gh (?:(?:issue|pr) (?:create|comment|edit|close)|api)\b)")
SEGMENT_END = re.compile(r"&&|\|\||[;|)`]|(?<!\\)\n")  # a backslash-newline continues the command
# each gh command that writes a record or a change, by the write it does
WRITES = {"gh issue create": "file", "gh pr create": "change", "gh issue comment": "comment", "gh pr comment": "change comment",
          "gh issue close": "resolve", "gh issue edit": "edit", "gh pr edit": "change edit"}
REST_WRITE = re.compile(r'issues(?:/(\d+)(/comments)?)?(?=[\s"\'?]|$)')
REST_PULLS = re.compile(r'/pulls(?=[\s"\'?]|$)')
BODY_FILE = re.compile(r"(?:--body-file[= ]|(?:-F|--field)[= ]body=@)[\"']?([^\s\"']+)")
TITLE = re.compile(r"(?<!\S)(--title|-t|(?:-f|-F|--field|--raw-field)[= ]title)[= ](\"[^\"]*\"|'[^']*'|[^\s\"']\S*)")
POSTED = re.compile(r"https://github\.com/([^/\s\"]+/[^/\s\"]+)/issues/(\d+)(?:#issuecomment-(\d+))?")


def trusted(record):
    """Whether an issue's or comment's author may write records, since anyone may comment on a public repository."""
    return record.get("authorAssociation") in TRUSTED


def cache_file(path, repo):
    """The file keeping PATH's last answer and ETag. Its key drops the `since` value, so a moving stamp reuses one file: an ETag names the content,
    so a key two reads share costs a full read at worst, never a wrong answer."""
    key = SINCE.sub("", f"{repo or os.environ.get('GH_REPO', '')} {path}")
    return CACHE / f"{hashlib.sha1(key.encode()).hexdigest()}.json"


def fetch(path, repo, tries):
    """The parsed JSON of one GET; None when it failed. It sends the kept ETag, since GitHub charges no rate limit for the 304
    that says the kept answer still holds, and every session's monitor and hooks read the same board."""
    file = cache_file(path, repo)
    try:
        kept = json.loads(file.read_text())
    except (OSError, ValueError):
        kept = None
    for _ in range(tries):  # gh's calls fail now and then, then pass on retry
        p = subprocess.run(["gh", "api", "-i", *(["-H", f"If-None-Match: {kept['etag']}"] if kept else []), path], capture_output=True, text=True)
        head, _, body = p.stdout.replace("\r\n", "\n").partition("\n\n")
        status = head.split(" ", 2)[1] if head.startswith("HTTP/") else ""
        if status == "304" and kept:
            return json.loads(kept["body"])
        if p.returncode == 0:
            etag = next((v for k, _, v in (line.partition(": ") for line in head.splitlines()[1:]) if k.lower() == "etag"), None)
            if etag:
                file.parent.mkdir(parents=True, exist_ok=True)
                spare = file.with_suffix(f".{os.getpid()}.tmp")  # renamed into place, so a reader in another session never meets half a file
                spare.write_text(json.dumps({"etag": etag, "body": body}))
                os.replace(spare, file)
            return json.loads(body)
        if status.startswith("4"):  # a missing label or issue stays missing on retry
            return None
    return None


def get(path, repo=None, paginate=True, tries=3):
    """The parsed JSON of a GET, every page joined when PAGINATE; None when it failed. REPO is `owner/name`, else the checkout's."""
    need("gh")
    path = re.sub(r"^repos\b", f"repos/{repo or '{owner}/{repo}'}", path)
    if not paginate:
        return fetch(path, repo, tries)
    # pages by `page=`, never gh's own paging, whose `Link` paths name `repositories/<id>/`, which a cloud session's proxy refuses
    size = int(m.group(1)) if (m := re.search(r"[?&]per_page=(\d+)", path)) else 30
    found = []
    for n in itertools.count(1):
        page = fetch(f"{path}{'&' if '?' in path else '?'}page={n}", repo, tries)
        if page is None:
            return None
        found += page
        if len(page) < size:
            return found


def issue(raw):
    """RAW, a REST issue or pull request, as a record."""
    merged = (raw.get("pull_request") or {}).get("merged_at")
    parent = raw.get("parent_issue_url")
    return {"number": raw["number"], "title": raw["title"], "body": raw["body"] or "", "url": raw["html_url"],
            "state": raw["state"].upper(), "stateReason": (raw.get("state_reason") or "").upper(), "createdAt": raw["created_at"],
            "closedAt": raw["closed_at"], "trusted": trusted({"authorAssociation": raw["author_association"]}), "labels": [x["name"] for x in raw["labels"]],
            "parent": parent and int(parent.rsplit("/", 1)[1]), "isPullRequest": "pull_request" in raw, "mergedAt": merged, "comments": []}


def note(raw):
    """RAW, a REST comment, as a record's comment."""
    return {"body": raw["body"], "url": raw["html_url"], "createdAt": raw["created_at"], "trusted": trusted({"authorAssociation": raw["author_association"]})}


def with_comments(found, repo=None):
    """FOUND with each row's comments, from one paginated read of the repository's comments since the oldest row that has any; None when a read failed."""
    pending = [i for i in found if i["_count"]]
    if pending:
        # a comment is updated no earlier than its issue was created, so this stamp leaves none out
        every = get(f"repos/issues/comments?per_page=100&since={min(i['createdAt'] for i in pending)}", repo)
        if every is None:
            return None
        by = {}
        for c in every:
            by.setdefault(int(c["issue_url"].rsplit("/", 1)[1]), []).append(note(c))
        for i in pending:
            i["comments"] = by.get(i["number"], [])
    for i in found:
        del i["_count"]
    return found


@functools.cache  # a label almost never changes, and one read of the board asks for it more than once
def scoped(project):
    if not project:  # the issue pane's tree of every issue asks with none
        return None
    label = team_settings.load(os.getcwd())["scope_prefix"] + project
    # the list, not the label: a missing label answers 404, which carries no ETag, while the list's ETag changes once a label is made
    found = get("repos/labels?per_page=100")
    return label if found and label in {x["name"] for x in found} else None


def issues(state="open", project=None, pulls=False, comments=True, since=None, repo=None):
    """The repository's issues, those labelled `scope:<project>` when PROJECT has that label, and its pull requests too when PULLS,
    newest first, only those updated since SINCE (an ISO time) when given; None when a read failed."""
    label = project and scoped(project)
    path = f"repos/issues?state={state}&per_page=100" + (f"&labels={quote(label)}" if label else "") + (f"&since={since}" if since else "")
    raw = get(path, repo)
    if raw is None:
        return None
    found = [{**issue(r), "_count": r["comments"]} for r in raw if pulls or "pull_request" not in r]
    return with_comments(found, repo) if comments else [{k: v for k, v in i.items() if k != "_count"} for i in found]


def fresh(number, repo=None, comments=True):
    """One issue, with its comments when COMMENTS, read now by its own reads; None when a read failed."""
    raw = get(f"repos/issues/{number}", repo, paginate=False)
    read = get(f"repos/issues/{number}/comments?per_page=100", repo) if comments else []
    return raw and read is not None and {**issue(raw), "comments": [note(c) for c in read]} or None


def comments_since(since):
    """Every comment updated since SINCE (an ISO time), as (issue number, comment); None when a read failed."""
    found = get(f"repos/issues/comments?per_page=100&since={since}")
    return None if found is None else [(int(r["issue_url"].rsplit("/", 1)[1]), note(r)) for r in found]


def changed_since(stamp):
    """Whether any issue or pull request changed since STAMP (an ISO time), by one cheap REST read of the newest; True when it failed, so the caller reads in full."""
    newest = get(f"repos/issues?state=all&per_page=1&since={stamp}", paginate=False)
    return newest is None or bool(newest)


def blockers(number):
    """The numbers of the open issues NUMBER waits on; None when the read failed."""
    found = get(f"repos/issues/{number}/dependencies/blocked_by")
    return None if found is None else [b["number"] for b in found if b["state"] == "open"]


def graphql(query, owner, name, *fields):
    found = run("gh", "api", "graphql", "-f", f"query={query}", "-f", f"owner={owner}", "-f", f"name={name}", *fields)
    return found and found["data"]["repository"]


def tree(project, nodes=None):
    """The open issues' nodes, those labelled `scope:<project>` when that label exists, else all, or NODES when given, each issue and comment
    marked `trusted`; None when a read failed."""
    nodes = nodes if nodes is not None else read_tree(project)
    for n in nodes or []:
        n["trusted"] = trusted(n)
        for c in n["comments"]["nodes"] + (n.get("subIssues") or {}).get("nodes", []):
            c["trusted"] = trusted(c)
    return nodes


def read_tree(project):
    need("gh")  # `run` reads a missing gh as a failed read, which hides the fix
    repo = get("repos", paginate=False)
    if repo is None:
        return None
    repo = {"owner": repo["owner"]["login"], "name": repo["name"]}
    label = scoped(project)
    scope = ["-f", f"labels[]={label}"] if label else []
    found_issues, after = [], []
    while True:  # a page is one point, so a project of more than 30 open issues pays one more per 30
        found = graphql(ISSUES, repo["owner"], repo["name"], *scope, *after)
        if found is None:
            return None
        found_issues += found["issues"]["nodes"]
        if not found["issues"]["pageInfo"]["hasNextPage"]:
            break
        after = ["-f", f"after={found['issues']['pageInfo']['endCursor']}"]
    shown = [t for n in found_issues for t in [t for t in n["subIssues"]["nodes"] if t["state"] == "CLOSED"][-SHOWN_CLOSED:]]
    if shown:
        asked = graphql(BLOCKERS % " ".join(f"i{k}: issue(number: {k}) {{ blockedBy(first: 20) {{ nodes {{ number state }} }} }}" for k in {t["number"] for t in shown}),
                        repo["owner"], repo["name"])
        if asked is None:
            return None
        for t in shown:
            t["blockedBy"] = asked[f"i{t['number']}"]["blockedBy"]
    return found_issues


def write(*argv, text=None):
    """The JSON a `gh api` write answers; it raises when the write failed, since a lost write must not pass for a done one."""
    need("gh")
    p = subprocess.run(["gh", "api", *argv], input=text, capture_output=True, text=True, check=True)
    return json.loads(p.stdout) if p.stdout.strip() else None


def node_id(number):
    found = get(f"repos/issues/{number}", paginate=False)
    if found is None:
        raise LookupError(f"cannot read #{number}")
    return found["id"]


def make_label(name):
    need("gh")
    subprocess.run(["gh", "label", "create", name, "--force"], capture_output=True, check=True)


def comment(number, text):
    """Posts TEXT as a comment on NUMBER; its url."""
    return write("-X", "POST", f"repos/{{owner}}/{{repo}}/issues/{number}/comments", "-F", "body=@-", text=text)["html_url"]


def file(title, body, labels) -> int:
    """Opens an issue; its number."""
    for name in labels:
        make_label(name)
    return write("-X", "POST", "repos/{owner}/{repo}/issues", "-f", f"title={title}", "-F", "body=@-",
                 *[f for name in labels for f in ("-f", f"labels[]={name}")], text=body)["number"]


def body(number):
    """NUMBER's body as GitHub keeps it; raises LookupError naming the cause when the read failed."""
    need("gh")
    # REST, not `gh issue`: GraphQL hits its rate limit while REST still works
    read = subprocess.run(["gh", "api", f"repos/{{owner}}/{{repo}}/issues/{number}", "-q", ".body"], capture_output=True, text=True)
    if read.returncode:
        # gh fills {owner}/{repo} from the working folder, or from GH_REPO
        # gh's own line keeps a missing issue or an auth failure from reading as a folder fault
        cause = (read.stderr.strip().splitlines() or ["no message"])[0]
        raise LookupError(f"cannot read #{number} ({cause}); if you are not in the repository's checkout, set GH_REPO=<owner>/<repo>")
    return read.stdout


def edit(number, text):
    write("-X", "PATCH", f"repos/{{owner}}/{{repo}}/issues/{number}", "-F", "body=@-", text=text)


def resolve(number, summary, completed=True):
    """Comments SUMMARY, then closes NUMBER, completed or not planned."""
    comment(number, summary)
    write("-X", "PATCH", f"repos/{{owner}}/{{repo}}/issues/{number}", "-f", "state=closed", "-f", f"state_reason={'completed' if completed else 'not_planned'}")


def order(later, earlier):
    """Records that LATER waits on EARLIER."""
    write("-X", "POST", f"repos/{{owner}}/{{repo}}/issues/{later}/dependencies/blocked_by", "-F", f"issue_id={node_id(earlier)}")


def nest(backlog, task):
    write("-X", "POST", f"repos/{{owner}}/{{repo}}/issues/{backlog}/sub_issues", "-F", f"sub_issue_id={node_id(task)}")


def label(number, name, remove=False):
    if remove:
        write("-X", "DELETE", f"repos/{{owner}}/{{repo}}/issues/{number}/labels/{quote(name)}")
    else:
        make_label(name)
        write("-X", "POST", f"repos/{{owner}}/{{repo}}/issues/{number}/labels", "-f", f"labels[]={name}")


def rest_call(command):
    """The gh issue command a REST write stands for, so one rule list covers both ways of writing."""
    if not command.startswith("gh api"):
        return command
    method = re.search(r"(?:-X|--method[= ])\s*(\w+)", command)
    method = method.group(1).upper() if method else "POST" if re.search(r"(?<!\S)(-f|-F|--field|--raw-field|--input)\b", command) else "GET"
    if method == "POST" and REST_PULLS.search(command):
        return "gh pr create"
    path = REST_WRITE.search(command)
    if not path or method not in ("POST", "PATCH"):
        return ""
    if path.group(2):
        return "gh issue comment" if method == "POST" else ""
    if path.group(1):
        return ("gh issue close" if "state=closed" in command else "gh issue edit") if method == "PATCH" else ""
    return "gh issue create" if method == "POST" else ""


def command(text):
    """The first gh call TEXT runs: `called`, the gh write it stands for, and `write`, its WRITES entry, each None for another call;
    `title`, its title's length; `inline body` and `body edit`, a body passed inline or an issue body changed in place; `body file`. None when TEXT runs no gh call."""
    found = GH_TEXT.search(text)
    if not found:
        return None
    segment = SEGMENT_END.split(text[found.start(1):])[0]
    call = rest_call(segment)
    called = next((c for c in WRITES if call.startswith(c)), None)
    title = TITLE.search(segment)
    posted = BODY_FILE.search(segment)
    return {"called": called, "write": WRITES.get(called), "title": title and len(title.group(2)) - (2 if title.group(2)[0] in "\"'" else 0),
            "inline body": bool(re.search(r"(?<!\S)(--body|-b)[= ]", segment)),
            "body edit": bool(re.match(r"gh issue edit\b", segment) and re.search(r"(?<!\S)(--body-file|-F|--body|-b)[= ]", segment)),
            "body file": posted and posted.group(1)}


def posted(output):
    """(url, body) of the first issue or comment url OUTPUT names, its body read back now, since a body file written by the same command
    is missing when a hook looks; only the first, since a body or a later command may cite another. None when it names none."""
    found = POSTED.search(output)
    if not found:
        return None
    repo, number, comment_id = found.groups()
    read = run("gh", "api", f"repos/{repo}/issues/comments/{comment_id}" if comment_id else f"repos/{repo}/issues/{number}") or {}
    return found.group(0), read.get("body") or ""

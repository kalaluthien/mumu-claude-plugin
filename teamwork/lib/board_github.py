"""The board on GitHub: issues and comments read by REST, which spends no GraphQL point, the issue pane's tree by GraphQL, and writes by `gh api`."""
import json
import re
import subprocess
from urllib.parse import quote

from issue_board import SHOWN_CLOSED
from json_command import run

TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}
# one point or two per read: GitHub charges each connection a node is asked for, so the sub-issues' blockers, the costliest part,
# are read only for the closed ones the board shows, by the second query
ISSUES = """query($owner: String!, $name: String!, $labels: [String!], $after: String) {
  repository(owner: $owner, name: $name) {
    issues(states: OPEN, first: 30, after: $after, labels: $labels, orderBy: {field: CREATED_AT, direction: ASC}) {
      nodes { number title url body authorAssociation parent { number } labels(first: 20) { nodes { name } } subIssuesSummary { total completed }
              subIssues(last: 50) { nodes { number title url state } }
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
BODY_FILE = re.compile(r"(?:--body-file[= ]|(?:-F|--field)[= ]body=@)[\"']?([^\s\"']+)")
TITLE = re.compile(r"(?<!\S)(--title|-t)[= ](\"[^\"]*\"|'[^']*'|[^\s\"']\S*)")
POSTED = re.compile(r"https://github\.com/([^/\s\"]+/[^/\s\"]+)/issues/(\d+)(?:#issuecomment-(\d+))?")


def trusted(record):
    """Whether an issue's or comment's author may write records, since anyone may comment on a public repository."""
    return record.get("authorAssociation") in TRUSTED


def get(path, repo=None, paginate=True, tries=3):
    """The parsed JSON of a GET, every page joined when PAGINATE; None when it failed. REPO is `owner/name`, else the checkout's."""
    path = path.replace("repos/", f"repos/{repo}/", 1) if repo else path.replace("repos/", "repos/{owner}/{repo}/", 1)
    for _ in range(tries):  # gh's calls fail now and then, then pass on retry
        p = subprocess.run(["gh", "api", *(["--paginate", "--slurp"] if paginate else []), path], capture_output=True, text=True)
        if p.returncode == 0:
            out = json.loads(p.stdout)
            return [x for page in out for x in page] if paginate else out
    return None


def issue(raw):
    """RAW, a REST issue or pull request, as a record."""
    merged = (raw.get("pull_request") or {}).get("merged_at")
    parent = raw.get("parent_issue_url")
    return {"number": raw["number"], "title": raw["title"], "body": raw["body"] or "", "url": raw["html_url"],
            "state": raw["state"].upper(), "stateReason": (raw.get("state_reason") or "").upper(), "createdAt": raw["created_at"],
            "closedAt": raw["closed_at"], "trusted": trusted({"authorAssociation": raw["author_association"]}), "labels": [{"name": x["name"]} for x in raw["labels"]],
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


def scoped(project):
    label = f"scope:{project}"
    # a REST read, which costs no GraphQL point; a missing label answers 404, which `run` reads as None
    return label if run("gh", "api", f"repos/{{owner}}/{{repo}}/labels/{label.replace(':', '%3A')}", "--jq", "{name}") else None


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
    newest = run("gh", "api", f"repos/{{owner}}/{{repo}}/issues?state=all&per_page=1&since={stamp}")
    return newest is None or bool(newest)


def blockers(number):
    """The numbers of the open issues NUMBER waits on; None when the read failed."""
    found = run("gh", "api", f"repos/{{owner}}/{{repo}}/issues/{number}/dependencies/blocked_by")
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
        for c in n["comments"]["nodes"]:
            c["trusted"] = trusted(c)
    return nodes


def read_tree(project):
    repo = run("gh", "api", "repos/{owner}/{repo}", "--jq", "{owner: .owner.login, name: .name}")
    if repo is None:
        return None
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
    p = subprocess.run(["gh", "api", *argv], input=text, capture_output=True, text=True, check=True)
    return json.loads(p.stdout) if p.stdout.strip() else None


def node_id(number):
    found = get(f"repos/issues/{number}", paginate=False)
    if found is None:
        raise LookupError(f"cannot read #{number}")
    return found["id"]


def make_label(name):
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

#!/usr/bin/env python3
"""Do one board operation through the board port, so a session writes the same way on any board.

usage: use-board.py <operation> <args>

`comment`, `decide`, `file` and `resolve` first refuse, exit 2 and post nothing, a text with a malformed key line, keyword line or section heading, naming the fix;
`file`, `title`, `decide` and an `edit` also refuse a title, summary line or decision that breaks the grammar's Plain words caps;
`file`, and an `edit` of a task numbered at or above the Goal cut-off, refuse a `## Goal` that names no flow of its changed part, as check-criteria.py does, unless the body edited held that defect already.

  read <issue> [--as worker|judge]      print its title, state, labels, parent, body and comments; as a worker without each `Judge note:` paragraph,
                                        which names probes of a criterion's implementation, as a judge without each `BLOCKED:` comment, which is worker history
  comment <issue> <body-file>           append the file's text as a comment; refused, nothing posted, when it holds a `decision` block, which `decide` posts
  file <title> <body-file> [label...] [--scope <folder>]   open an issue in the folder, a path from the repository root ('' the root; a manager's own
                                        project folder when none is given, else the root), refused when the repository has no such folder; print its url;
                                        its `[task]` and `depends on` lines link it, refused when they make a cycle, a second parent or name an unknown issue
  edit <issue> <diff-file> <line> --base <sha>   change the body by a diff, with the keyword line [edit-issue-body.py](edit-issue-body.py) posts first;
                                        refused when the body no longer has the `body sha` `read` printed, the sha given as `--base`
  title <issue> <title>                 change the title
  resolve <issue> <summary-file> [--not-planned]   close it with the summary, `REPORTED: ` put first when it lacks it
  reopen <issue>                        open a closed issue again
  decide <issue> <body-file>            comment the text, `DECIDED: ` put first when it lacks it; a `decision` block is refused,
                                        nothing posted, when it breaks a rule of the grammar's Decisions section
  label <issue> <name> [--remove]"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board  # noqa: E402
import criteria_check  # noqa: E402
import decisions  # noqa: E402
import issue_state  # noqa: E402
from judge_note import without_judge_note  # noqa: E402
import own_reports  # noqa: E402
import session  # noqa: E402
import team_names  # noqa: E402


def keep_own(url, text):
    """A manager's own report is news to no one, so its heartbeat is told not to feed it back."""
    if issue_state.keyword(text) == issue_state.INFORM and team_names.role(session.sessions()[1].get("name")) == "manager":
        own_reports.note(url)


def read_text(path):
    return pathlib.Path(path).read_text()


def keyed(keyword, path):
    """The text of PATH, KEYWORD put first when it lacks it, so a text the verb names gets its keyword rather than a refusal no caller can read."""
    text = read_text(path)
    return text if text.startswith(keyword) else f"{keyword} {text}"


def read_issue(operands):
    role = operands[2] if len(operands) == 3 and operands[1] == "--as" and operands[2] in ("worker", "judge") else None
    if len(operands) == 3 and not role:
        print(__doc__, file=sys.stderr)
        return 2
    issue = board.fresh(operands[0]) or sys.exit(f"use-board: cannot read #{operands[0]}")
    print(f"#{issue['number']} {issue_state.title(issue)}\nstate: {issue['state']}\n{'scope: ' + (issue['scope'] or '(repository root)') + chr(10) if 'scope' in issue else ''}labels: {', '.join(issue['labels'])}\nparent: {issue['parent']}\nbody sha: {board.body_sha(issue['body'])}\n\n{issue['body']}")
    for comment in issue["comments"]:
        if role == "judge" and issue_state.keyword(comment["body"]) == "BLOCKED":
            continue
        print(f"\n--- {comment['url']}\n{without_judge_note(comment['body']) if role == 'worker' else comment['body']}")
    return 0


def post_comment(operands):
    text = read_text(operands[1])
    # a decision block binds, so only `decide`, which holds it to the grammar's rules, may post one
    if issue_state.decision(text) is not None:
        sys.exit(f"use-board: nothing posted: {operands[1]} holds a decision block; post it by `decide`, which checks it")
    url = board.comment(operands[0], text)
    keep_own(url, text)
    print(url)
    return 0


def file_issue(operands):
    # a Goal that names no flow of its changed part would sit on the board until a lint found it, so it is refused before it is filed
    refused = criteria_check.goal_refusals(read_text(operands[1]))
    if refused:
        print("use-board: nothing posted, the file has defects:\n- " + "\n- ".join(refused), file=sys.stderr)
        return 2
    rest, scope = operands[2:], {}
    if "--scope" in rest:
        at = rest.index("--scope")
        if at + 1 >= len(rest):
            print(__doc__, file=sys.stderr)
            return 2
        scope, rest = {"scope": rest[at + 1]}, rest[:at] + rest[at + 2:]
    print(board.fresh(board.file(operands[0], read_text(operands[1]), rest, **scope), comments=False)["url"])
    return 0


def edit_body(operands):
    return subprocess.run([sys.executable, str(HERE / "edit-issue-body.py"), *operands]).returncode


def resolve_issue(operands):
    board.resolve(operands[0], keyed("REPORTED:", operands[1]), "--not-planned" not in operands[2:])
    closed = board.fresh(operands[0])
    if closed and closed["comments"]:
        keep_own(closed["comments"][-1]["url"], closed["comments"][-1]["body"])
    return 0


def retitle_issue(operands):
    board.retitle(*operands)
    return 0


def reopen_issue(operands):
    board.reopen(operands[0])
    return 0


def decide_issue(operands):
    said = keyed("DECIDED:", operands[1])
    refused = decisions.refusals(operands[0], said, decisions.read(operands[0], board.fresh)) if issue_state.decision(said) else []
    if refused:
        sys.exit(f"use-board: nothing posted: {'; '.join(refused)}")
    print(board.comment(operands[0], said))
    return 0


def label_issue(operands):
    board.label(operands[0], operands[1], "--remove" in operands[2:])
    return 0


# verb -> (whether it takes that many operands, what it does); any other call prints the usage
VERBS = {"read": (lambda count: count in (1, 3), read_issue), "comment": (lambda count: count == 2, post_comment), "file": (lambda count: count >= 2, file_issue),
         "edit": (lambda count: count in (3, 5), edit_body), "resolve": (lambda count: count in (2, 3), resolve_issue), "title": (lambda count: count == 2, retitle_issue),
         "reopen": (lambda count: count == 1, reopen_issue), "decide": (lambda count: count == 2, decide_issue), "label": (lambda count: count in (2, 3), label_issue)}


def main(args):
    verb, *operands = args or [""]
    try:
        # a text that no code reads as meant would leave an issue unrouted or a question unasked, so it is refused with its fix
        found = issue_state.defects(verb, read_text(operands[1])) if verb in ("comment", "decide", "file", "resolve") and len(operands) >= 2 else []
        found += issue_state.defects("title", operands[0] if verb == "file" else operands[-1]) if verb in ("file", "title") and len(operands) >= 2 else []
        if found:
            print(f"use-board: nothing posted, the {verb} has defects:\n- " + "\n- ".join(found) + f"\nthe grammar is {issue_state.GRAMMAR}", file=sys.stderr)
            return 2
        accepts, run = VERBS.get(verb, (lambda count: False, None))
        if not accepts(len(operands)):
            print(__doc__, file=sys.stderr)
            return 2
        return run(operands)
    except (OSError, LookupError, subprocess.CalledProcessError) as e:
        sys.exit(f"use-board: {e}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

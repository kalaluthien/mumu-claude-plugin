#!/usr/bin/env python3
"""Do one board operation through the board port, so a session writes the same way on any board.

usage: use-board.py <operation> <args>

`comment`, `decide`, `file` and `resolve` first refuse, exit 2 and post nothing, a text with a malformed key line, keyword line or section heading, naming the fix;
`file`, `title`, `decide` and an `edit` also refuse a title, summary line or decision that breaks the grammar's Plain words caps.

  read <issue>                          print its title, state, labels, parent, body and comments
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
import decisions  # noqa: E402
import issue_state  # noqa: E402
import own_reports  # noqa: E402
import session  # noqa: E402
import team_names  # noqa: E402


def keep_own(url, text):
    """A manager's own report is news to no one, so its heartbeat is told not to feed it back."""
    if issue_state.keyword(text) == issue_state.INFORM and team_names.role(session.sessions()[1].get("name")) == "manager":
        own_reports.note(url)


def main(args):
    verb, *operands = args or [""]
    text = lambda path: pathlib.Path(path).read_text()
    # the verb names the keyword, so a text that lacks it gets it rather than a refusal no caller can read
    keyed = lambda keyword, path: text(path) if text(path).startswith(keyword) else f"{keyword} {text(path)}"
    try:
        # a text that no code reads as meant would leave an issue unrouted or a question unasked, so it is refused with its fix
        found = issue_state.defects(verb, text(operands[1])) if verb in ("comment", "decide", "file", "resolve") and len(operands) >= 2 else []
        found += issue_state.defects("title", operands[0] if verb == "file" else operands[-1]) if verb in ("file", "title") and len(operands) >= 2 else []
        if found:
            print(f"use-board: nothing posted, the {verb} has defects:\n- " + "\n- ".join(found) + f"\nthe grammar is {issue_state.GRAMMAR}", file=sys.stderr)
            return 2
        if verb == "read" and len(operands) == 1:
            issue = board.fresh(operands[0]) or sys.exit(f"use-board: cannot read #{operands[0]}")
            print(f"#{issue['number']} {issue_state.title(issue)}\nstate: {issue['state']}\n{'scope: ' + (issue['scope'] or '(repository root)') + chr(10) if 'scope' in issue else ''}labels: {', '.join(issue['labels'])}\nparent: {issue['parent']}\nbody sha: {board.body_sha(issue['body'])}\n\n{issue['body']}")
            for comment in issue["comments"]:
                print(f"\n--- {comment['url']}\n{comment['body']}")
        elif verb == "comment" and len(operands) == 2:
            # a decision block binds, so only `decide`, which holds it to the grammar's rules, may post one
            if issue_state.decision(text(operands[1])) is not None:
                sys.exit(f"use-board: nothing posted: {operands[1]} holds a decision block; post it by `decide`, which checks it")
            url = board.comment(operands[0], text(operands[1]))
            keep_own(url, text(operands[1]))
            print(url)
        elif verb == "file" and len(operands) >= 2:
            rest = operands[2:]
            scope = {}
            if "--scope" in rest:
                at = rest.index("--scope")
                if at + 1 >= len(rest):
                    print(__doc__, file=sys.stderr)
                    return 2
                scope, rest = {"scope": rest[at + 1]}, rest[:at] + rest[at + 2:]
            print(board.fresh(board.file(operands[0], text(operands[1]), rest, **scope), comments=False)["url"])
        elif verb == "edit" and len(operands) in (3, 5):
            return subprocess.run([sys.executable, str(HERE / "edit-issue-body.py"), *operands]).returncode
        elif verb == "resolve" and len(operands) in (2, 3):
            board.resolve(operands[0], keyed("REPORTED:", operands[1]), "--not-planned" not in operands[2:])
            closed = board.fresh(operands[0])
            if closed and closed["comments"]:
                keep_own(closed["comments"][-1]["url"], closed["comments"][-1]["body"])
        elif verb == "title" and len(operands) == 2:
            board.retitle(*operands)
        elif verb == "reopen" and len(operands) == 1:
            board.reopen(operands[0])
        elif verb == "decide" and len(operands) == 2:
            said = keyed("DECIDED:", operands[1])
            refused = decisions.refusals(operands[0], said, decisions.read(operands[0], board.fresh)) if issue_state.decision(said) else []
            if refused:
                sys.exit(f"use-board: nothing posted: {'; '.join(refused)}")
            print(board.comment(operands[0], said))
        elif verb == "label" and len(operands) in (2, 3):
            board.label(operands[0], operands[1], "--remove" in operands[2:])
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except (OSError, LookupError, subprocess.CalledProcessError) as e:
        sys.exit(f"use-board: {e}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

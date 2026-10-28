#!/usr/bin/env python3
"""Do one board operation through the board port, so a session writes the same way on any board.

usage: use-board.py <operation> <args>

  read <issue>                          print its title, state, labels, parent, body and comments
  comment <issue> <body-file>           append the file's text as a comment
  file <title> <body-file> [label...]   open an issue; print its url
  edit <issue> <diff-file> <line>       change the body by a diff, with the keyword line [edit-issue-body.py](edit-issue-body.py) posts first
  title <issue> <title>                 change the title
  resolve <issue> <summary-file> [--not-planned]
  reopen <issue>                        open a closed issue again
  decide <issue> <body-file>            comment a text that opens with `DECIDED:`
  order <later> <earlier>               record that LATER waits on EARLIER
  nest <issue> <task>                   put TASK under the nearest backlog at or above ISSUE
  label <issue> <name> [--remove]"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board  # noqa: E402
import issue_state  # noqa: E402


def main(args):
    verb, *operands = args or [""]
    text = lambda path: pathlib.Path(path).read_text()
    try:
        if verb == "read" and len(operands) == 1:
            issue = board.fresh(operands[0]) or sys.exit(f"use-board: cannot read #{operands[0]}")
            print(f"#{issue['number']} {issue_state.title(issue)}\nstate: {issue['state']}\nlabels: {', '.join(issue['labels'])}\nparent: {issue['parent']}\n\n{issue['body']}")
            for comment in issue["comments"]:
                print(f"\n--- {comment['url']}\n{comment['body']}")
        elif verb == "comment" and len(operands) == 2:
            print(board.comment(operands[0], text(operands[1])))
        elif verb == "file" and len(operands) >= 2:
            print(board.fresh(board.file(operands[0], text(operands[1]), operands[2:]), comments=False)["url"])
        elif verb == "edit" and len(operands) == 3:
            return subprocess.run([sys.executable, str(HERE / "edit-issue-body.py"), *operands]).returncode
        elif verb == "resolve" and len(operands) in (2, 3) and text(operands[1]).startswith("REPORTED:"):
            board.resolve(operands[0], text(operands[1]), "--not-planned" not in operands[2:])
        elif verb == "title" and len(operands) == 2:
            board.retitle(*operands)
        elif verb == "reopen" and len(operands) == 1:
            board.reopen(operands[0])
        elif verb == "decide" and len(operands) == 2 and text(operands[1]).startswith("DECIDED:"):
            print(board.comment(operands[0], text(operands[1])))
        elif verb == "order" and len(operands) == 2:
            board.order(*operands)
        elif verb == "nest" and len(operands) == 2:
            board.nest(*operands)
        elif verb == "label" and len(operands) in (2, 3):
            board.label(operands[0], operands[1], "--remove" in operands[2:])
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except (OSError, LookupError, subprocess.CalledProcessError) as e:
        sys.exit(f"use-board: {e}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

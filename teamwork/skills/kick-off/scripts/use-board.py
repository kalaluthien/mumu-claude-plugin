#!/usr/bin/env python3
"""usage: use-board.py <operation> <args>

Do one board operation through the board port, so a session writes the same way on any board:
  read <issue>                          print its title, state, labels, parent, body and comments
  comment <issue> <body-file>           append the file's text as a comment
  file <title> <body-file> [label...]   open an issue; print its url
  edit <issue> <diff-file> <line>       change the body by a diff, with the keyword line [edit-issue-body.py](edit-issue-body.py) posts first
  resolve <issue> <summary-file> [--not-planned]
  decide <issue> <body-file>            comment a text that opens with `DECIDED:`
  order <later> <earlier>               record that LATER waits on EARLIER
  nest <backlog> <task>                 put TASK under BACKLOG
  label <issue> <name> [--remove]"""
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board  # noqa: E402

verb, *a = sys.argv[1:] or [""]
text = lambda path: pathlib.Path(path).read_text()
try:
    if verb == "read" and len(a) == 1:
        i = board.fresh(a[0]) or sys.exit(f"use-board: cannot read #{a[0]}")
        print(f"#{i['number']} {i['title']}\nstate: {i['state']}\nlabels: {', '.join(i['labels'])}\nparent: {i['parent']}\n\n{i['body']}")
        for c in i["comments"]:
            print(f"\n--- {c['url']}\n{c['body']}")
    elif verb == "comment" and len(a) == 2:
        print(board.comment(a[0], text(a[1])))
    elif verb == "file" and len(a) >= 2:
        print(board.fresh(board.file(a[0], text(a[1]), a[2:]), comments=False)["url"])
    elif verb == "edit" and len(a) == 3:
        sys.exit(subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("edit-issue-body.py")), *a]).returncode)
    elif verb == "resolve" and len(a) in (2, 3):
        board.resolve(a[0], text(a[1]), "--not-planned" not in a[2:])
    elif verb == "decide" and len(a) == 2 and text(a[1]).startswith("DECIDED:"):
        print(board.comment(a[0], text(a[1])))
    elif verb == "order" and len(a) == 2:
        board.order(*a)
    elif verb == "nest" and len(a) == 2:
        board.nest(*a)
    elif verb == "label" and len(a) in (2, 3):
        board.label(a[0], a[1], "--remove" in a[2:])
    else:
        sys.exit(__doc__)
except (OSError, LookupError, subprocess.CalledProcessError) as e:
    sys.exit(f"use-board: {e}")

#!/usr/bin/env python3
"""usage: edit-issue-body.py <issue> <diff-file> <keyword line>

Edit an issue's body by a unified diff of it: post a comment of the keyword line and the diff in a `diff` fence, then
apply the diff to the body. A diff that does not apply to the current body changes nothing, comment included."""
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board  # noqa: E402

issue, diff_file, line = sys.argv[1:4]
diff = pathlib.Path(diff_file).read_text()
# patch accepts an empty diff, which would post a comment that changes nothing
if not diff.strip():
    sys.exit(f"edit-issue-body: {diff_file} is empty, so nothing was posted or changed")
work = pathlib.Path(tempfile.mkdtemp())
body = work / "body.md"
# the web editor saves CRLF, which a diff written against the shown text never matches
try:
    body.write_text(board.body(issue).replace("\r\n", "\n"))
except LookupError as e:
    print(f"edit-issue-body: {e}", file=sys.stderr)
    sys.exit(2)
# --forward: an applied diff reads as reversed, which a bare dry run would accept
check = subprocess.run(["patch", "--forward", "--batch", "--dry-run", "-s", str(body), diff_file], capture_output=True, text=True)
if check.returncode:
    sys.exit(f"edit-issue-body: the diff does not apply to #{issue}'s body, so nothing was posted or changed:\n{check.stdout}{check.stderr}")
fence = "`" * max([3] + [len(run) + 1 for run in re.findall(r"`+", diff)])
comment = work / "comment.md"
comment.write_text(f"{line}\n\n{fence}diff\n{diff}{'' if diff.endswith(chr(10)) else chr(10)}{fence}\n")
print(board.comment(issue, comment.read_text()))
subprocess.run(["patch", "--forward", "--batch", "-s", str(body), diff_file], check=True)
board.edit(issue, body.read_text())
print(f"edit-issue-body: #{issue}'s body now carries the diff its new comment holds")

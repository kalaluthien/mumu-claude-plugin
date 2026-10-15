#!/usr/bin/env python3
"""usage: edit-issue-body.py <issue> <diff-file> <keyword line>

Edit an issue's body by a unified diff of it: post a comment of the keyword line and the diff in a `diff` fence, then
apply the diff to the body. A diff that does not apply to the current body changes nothing, comment included."""
import pathlib
import re
import subprocess
import sys
import tempfile

issue, diff_file, line = sys.argv[1:4]
diff = pathlib.Path(diff_file).read_text()
work = pathlib.Path(tempfile.mkdtemp())
body = work / "body.md"
# the web editor saves CRLF, which a diff written against the shown text never matches
body.write_text(subprocess.run(["gh", "issue", "view", issue, "--json", "body", "-q", ".body"],
                               capture_output=True, text=True, check=True).stdout.replace("\r\n", "\n"))
# --forward: an applied diff reads as reversed, which a bare dry run would accept
check = subprocess.run(["patch", "--forward", "--batch", "--dry-run", "-s", str(body), diff_file], capture_output=True, text=True)
if check.returncode:
    sys.exit(f"edit-issue-body: the diff does not apply to #{issue}'s body, so nothing was posted or changed:\n{check.stdout}{check.stderr}")
fence = "`" * max([3] + [len(run) + 1 for run in re.findall(r"`+", diff)])
comment = work / "comment.md"
comment.write_text(f"{line}\n\n{fence}diff\n{diff}{'' if diff.endswith(chr(10)) else chr(10)}{fence}\n")
subprocess.run(["gh", "issue", "comment", issue, "--body-file", str(comment)], check=True)
subprocess.run(["patch", "--forward", "--batch", "-s", str(body), diff_file], check=True)
subprocess.run(["gh", "issue", "edit", issue, "--body-file", str(body)], check=True)
print(f"edit-issue-body: #{issue}'s body now carries the diff its new comment holds")

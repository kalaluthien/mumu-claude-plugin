#!/usr/bin/env python3
"""Edit an issue's body by a unified diff of it: post a comment of the keyword line and the diff in a `diff` fence, then
apply the diff to the body. A diff that does not apply to the current body, or that adds a defect to it or has a keyword line that is not one
`DECIDED:` line, changes nothing, comment included, and exits 2 naming the fix. With `--base <sha>`, the `body sha` `use-board.py read` printed, a body that changed since
is refused too, since a diff made from an older body would put its old text back.

usage: edit-issue-body.py <issue> <diff-file> <keyword line> [--base <sha>]"""
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import board  # noqa: E402
import issue_state  # noqa: E402


def main(args):
    base = None
    if "--base" in args:
        at = args.index("--base")
        base, args = args[at + 1] if at + 1 < len(args) else None, args[:at] + args[at + 2:]
        if not base:
            print(__doc__, file=sys.stderr)
            return 2
    if len(args) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    issue, diff_file, line = args
    diff = pathlib.Path(diff_file).read_text()
    # patch accepts an empty diff, which would post a comment that changes nothing
    if not diff.strip():
        sys.exit(f"edit-issue-body: {diff_file} is empty, so nothing was posted or changed")
    work = pathlib.Path(tempfile.mkdtemp())
    fence = "`" * max([3] + [len(run) + 1 for run in re.findall(r"`+", diff)])
    comment = f"{line}\n\n{fence}diff\n{diff}{'' if diff.endswith(chr(10)) else chr(10)}{fence}\n"
    found = issue_state.defects("edit-line", line)
    if found:
        print(defect_text(found), file=sys.stderr)
        return 2
    refusal = []

    def land():
        # read again on each try: a board that lost a write race runs this again from the newer body, so --base holds against that write too
        refusal.clear()
        body = work / "body.md"
        # the web editor saves CRLF, which a diff written against the shown text never matches
        body.write_text(board.body(issue).replace("\r\n", "\n"))
        if base and board.body_sha(body.read_text()) != base:
            refusal.append((1, f"edit-issue-body: #{issue}'s body changed since you read it (its body sha is {board.body_sha(body.read_text())}, not {base}), so nothing was posted or changed: read it again and make the diff from that body"))
            return None
        # --forward: an applied diff reads as reversed, which a bare dry run would accept
        check = subprocess.run(["patch", "--forward", "--batch", "--dry-run", "-s", str(body), diff_file], capture_output=True, text=True)
        padded = False
        if check.returncode and not body.read_text().endswith("\n"):
            # `gh issue view` prints the stored body with a newline it lacks, so a diff made from that output ends in one the body has not
            body.write_text(body.read_text() + "\n")
            retry = subprocess.run(["patch", "--forward", "--batch", "--dry-run", "-s", str(body), diff_file], capture_output=True, text=True)
            padded = retry.returncode == 0
            if not padded:
                body.write_text(body.read_text()[:-1])
        if check.returncode and not padded:
            refusal.append((1, f"edit-issue-body: the diff does not apply to #{issue}'s body, so nothing was posted or changed:\n{check.stdout}{check.stderr}"))
            return None
        applied = subprocess.run(["patch", "--forward", "--batch", "-s", "-o", "-", str(body), diff_file], capture_output=True, text=True)
        # a defect the body already held does not block the edit that may fix it
        found = issue_state.defects("edit-body", applied.stdout, body.read_text())
        if found:
            refusal.append((2, defect_text(found)))
            return None
        try:
            board.check_links(issue, applied.stdout)
        except LookupError as e:
            refusal.append((1, f"edit-issue-body: {e}"))
            return None
        url = board.comment(issue, comment)
        board.edit(issue, applied.stdout[:-1] if padded and applied.stdout.endswith("\n") else applied.stdout)
        return url
    # the check, the comment and the body land together on a board that can, so a refused edit leaves no comment saying it was made
    try:
        url = board.atomic(land)
    except LookupError as e:
        print(f"edit-issue-body: {e}", file=sys.stderr)
        return 2
    if refusal:
        code, message = refusal[0]
        print(message, file=sys.stderr)
        return code
    print(url)
    print(f"edit-issue-body: #{issue}'s body now carries the diff its new comment holds")


def defect_text(found):
    return "edit-issue-body: nothing posted or changed, the edit has defects:\n- " + "\n- ".join(found) + f"\nthe grammar is {issue_state.GRAMMAR}"


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

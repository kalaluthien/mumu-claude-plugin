"""The files of a local board that hold every issue of the repository's GitHub board: what `copy-board.py github <kind>` writes.

Each issue keeps its number, title, labels, state and reason, times and body; its comments follow in order. A GitHub author the board does not trust
(`board_github.trusted`) is skipped, body or comment, since the local boards trust every record and a copy would make that text an instruction.
A GitHub issue or comment url inside a kept text becomes the local board's url for the same record, so a `supersedes:` or `answers:` url binds.
`floor` holds the highest issue or pull-request number, so a new local issue never shares a number with a pull request that a commit cites."""
import json
import re

import board_github
import board_records

URL = re.compile(r"https://github\.com/([^/\s)\"'>]+/[^/\s)\"'>]+)/issues/(\d+)(?:#issuecomment-(\d+))?")
REASONS = {"COMPLETED": "COMPLETED", "NOT_PLANNED": "NOT_PLANNED", "REOPENED": "REOPENED"}


def read():
    """(every issue with its comments, the numbers of the pull requests), oldest first; LookupError when GitHub could not be read."""
    found = board_github.issues("all", pulls=True)
    if found is None:
        raise LookupError("the GitHub board could not be read, so nothing was copied")
    pulls = sorted(record["number"] for record in found if record["isPullRequest"])
    return sorted((record for record in found if not record["isPullRequest"]), key=lambda record: record["number"]), pulls


def comment_id(note):
    found = URL.search(note["url"])
    return found and found.group(3)


def repository(issues):
    """The `owner/repo` the issues come from, read from their own urls; None for no issue."""
    found = next((URL.search(record["url"]) for record in issues), None)
    return found and found.group(1)


def rewriter(kept, url, home):
    """A function that turns the urls of repository HOME in a text into URL(path) forms of the same records; another repository's url stays as written.
    KEPT is {issue number: [comment ids in kept order]}."""
    def swap(found):
        number, said = int(found.group(2)), found.group(3)
        if found.group(1) != home or number not in kept:
            return found.group(0)
        if not said:
            return url(str(number))
        if said not in kept[number]:
            return found.group(0)
        return f"{url(str(number))}#comment-{kept[number].index(said) + 1}"
    return lambda text: URL.sub(swap, text)


def files(issues, pulls, store):
    """({path: text} of the board holding ISSUES, the count of untrusted issues skipped, the count of untrusted comments skipped).
    STORE names the urls, and receives nothing."""
    store.refresh()  # a git board learns its folder, which its urls name, on its first read
    trusted = [record for record in issues if record["trusted"]]
    skipped_comments = sum(1 for record in trusted for note in record["comments"] if not note["trusted"])
    kept = {record["number"]: [comment_id(note) for note in record["comments"] if note["trusted"]] for record in trusted}
    swap = rewriter(kept, store.url, repository(issues))
    out = {}
    for record in trusted:
        number = record["number"]
        out[f"{number}/body.md"] = swap(record["body"])
        out[f"{number}/issue.json"] = json.dumps({
            "title": record["title"], "labels": record["labels"], "state": record["state"], "reason": REASONS.get(record["stateReason"], ""),
            "createdAt": record["createdAt"], "closedAt": record["closedAt"], "updatedAt": board_records.stamp(),
            "commentTimes": [note["createdAt"] for note in record["comments"] if note["trusted"]]})
        for position, note in enumerate((note for note in record["comments"] if note["trusted"]), 1):
            out[f"{number}/comments/{position:04d}.md"] = swap(note["body"])
    out[board_records.FLOOR] = f"{max([*pulls, *(record['number'] for record in issues)], default=0)}\n"
    return out, len(issues) - len(trusted), skipped_comments

"""The past work a worker's read of a task prints after it: the tasks related to it and the recent commits on the files its body names,
read from the board and `git log` alone. `lines(task, records)` takes the task's record and every record of the board."""
import re
import subprocess

import decisions
import task_links

TASKS, COMMITS, DAYS = 5, 5, 30  # the bounds of #1582's routing decision, about 30 lines
STOP = set("a an and as at be by for from in into is it its no not of on or the to with".split())
# a landed commit names its task as `(task 12)`, an older one its pull request as `(#12)`
SUBJECT_TASK = re.compile(r"\((?:task |#)(\d+)\)")
NAMED = re.compile(r"`([^`\s]+)[^`]*`")  # a command's first word names its script
REVERSED = re.compile(r"(\d+)#comment-(\d+)$")


def git(*argv):
    done = subprocess.run(["git", *argv], capture_output=True, text=True)
    return done.stdout.splitlines() if done.returncode == 0 else []


def title_words(title):
    return {word for word in re.findall(r"[a-z0-9]+", title.lower()) if word not in STOP}


def named_files(body, scope, tracked):
    """The tracked files BODY names in backticks: a path from the root, or the end of the path of one tracked file under SCOPE."""
    found = []
    for name in NAMED.findall(body):
        matches = [name] if name in tracked else [path for path in tracked if path.startswith(f"{scope}/".lstrip("/")) and path.endswith("/" + name)]
        if len(matches) == 1:
            found.append(matches[0])
    return list(dict.fromkeys(found))


def picked(record):
    """At most two decisions: the latest, then the newest that reversed an earlier one, each tagged with what it reversed."""
    typed = decisions.typed(record["number"], record)
    chosen = typed[-1:] + [decision for decision in reversed(typed[:-1]) if decision["supersedes"]][:1]
    out = []
    for decision in sorted(chosen, key=lambda decision: decision["index"]):
        found = REVERSED.search(decision["supersedes"])
        out.append(f"  DECIDED: {decision['decision'][:120]}" + (f" (reverses #{found[1]} comment {found[2]})" if found else ""))
    return out


def related(task, records, files, top):
    """Up to TASKS (number, why) pairs: linked tasks, then tasks whose landed commits touched FILES, then tasks sharing two title words; newest first within each."""
    tasks = {number: record for number, record in records.items() if number != task["number"]}
    parent = task.get("parent")
    linked = {number: "its parent" for number in [parent] if number}
    linked |= {number: "a sibling part" for number in (task_links.parts(records[parent]["body"]) if parent in records else [])}
    linked |= {number: "its part" for number in task_links.parts(task["body"])}
    linked |= {number: "a task it waits on" for number in task_links.depends(task)}
    touched = {}
    for path in files:
        for subject in git("-C", top, "log", "--format=%s", "--", path):
            for number in map(int, SUBJECT_TASK.findall(subject)):
                touched.setdefault(number, f"its commits touched {path.rsplit('/', 1)[-1]}")
    words = title_words(task["title"])
    shared = {number: f"shares {len(common)} title words" for number, record in tasks.items()
              if len(common := words & title_words(record["title"])) >= 2}
    out = []
    for tier in (linked, touched, shared):
        for number in sorted(tier, reverse=True):
            if number in tasks and number not in dict(out):
                out.append((number, tier[number]))
    return out[:TASKS]


def lines(task, records):
    """The `related work:` block for TASK."""
    top = git("rev-parse", "--show-toplevel")[0]
    tracked = set(git("-C", top, "ls-files"))
    files = named_files(task["body"], task["scope"], tracked)
    out = ["related work, from the board and git log:"]
    found = related(task, records, files, top)
    for number, why in found:
        record = records[number]
        out.append(f"- #{number} {record['state']}: {record['title']} ({why})")
        out += picked(record)
    if not found:
        out.append("- no linked task, none whose commits touched a file it names, none sharing two title words")
    commits = git("-C", top, "log", f"--since={DAYS}.days.ago", f"-n{COMMITS}", "--format=%h %cd %s", "--date=short", "--", *files) if files else []
    names = ", ".join(path.rsplit("/", 1)[-1] for path in files)
    out.append(f"commits in the last {DAYS} days on {names}:" if files else "commits: the body names no tracked file")
    out += [f"- {commit}" for commit in commits] or ([f"- none in the last {DAYS} days"] if files else [])
    return out

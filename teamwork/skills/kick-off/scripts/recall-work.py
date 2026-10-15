#!/usr/bin/env python3
"""usage: recall-work.py [<words>...] [--path <file>]... [--before <date>] [--top <n>]

Print the earlier issues and pull requests of this repository most related to WORDS and to the history of each PATH,
best first: each line is `#<n> <kind> <state> <title>`, then the first line of each of its comments
that opens with a keyword of issue-grammar.md. `--before` sees the repository as it stood at DATE, to replay a past kick-off."""
import argparse
import collections
import json
import math
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import issue_state  # noqa: E402

STOP = set("a an and as at be by for from in into is it its no not of on or the to with".split())
# a file's newest commits say what it is now, its oldest why it exists, so both ends of its history weigh most
PATH_WEIGHT = 3.0
# work continues what was filed just before it: an item's score grows up to 9x, halving per 5 items filed since;
# tuned by replaying 30 past tasks against the earlier issues each cites
RECENT_GAIN, RECENT_HALF_LIFE = 8, 5


def run(*argv, tries=3):
    for left in reversed(range(tries)):  # gh's list calls fail now and then, then pass on retry
        p = subprocess.run(argv, capture_output=True, text=True)
        if p.returncode == 0 or not left:
            break
    if p.returncode:
        sys.exit(f"recall-work.py: `{' '.join(argv[:3])}` failed: {p.stderr.strip()}")
    return p.stdout


def words(text):
    return [re.sub(r"(ing|ed|es|s)$", "", w) if len(w) > 4 else w
            for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 1]


def load(before):
    fields = "number,title,body,createdAt,state"
    issues = json.loads(run("gh", "issue", "list", "--state", "all", "--limit", "2000", "--json",
                            fields + ",comments,stateReason,labels"))
    prs = json.loads(run("gh", "pr", "list", "--state", "all", "--limit", "2000", "--json",
                         fields + ",comments,mergedAt,closingIssuesReferences"))
    items = {}
    for item in issues + prs:
        if before and item["createdAt"] >= before:
            continue
        comments = [c["body"] for c in item["comments"] if not before or c["createdAt"] < before]
        if "mergedAt" in item:
            kind, state = "PR", "merged" if item["mergedAt"] else item["state"].lower()
        else:
            kind = "backlog" if any(label["name"] == "backlog" for label in item["labels"]) else "issue"
            state = "open" if item["state"] == "OPEN" else (item["stateReason"] or "closed").lower().replace("_", " ")
        items[item["number"]] = {
            "head": f"#{item['number']} {kind} {state}: {item['title']}",
            "text": " ".join([item["title"]] * 3 + [item["body"], *comments]),
            "records": [text.strip().splitlines()[0][:160] for text in comments if issue_state.keyword(text)],
            "closes": [c["number"] for c in item.get("closingIssuesReferences", [])],
        }
    return items


def text_scores(items, query):
    """BM25 of the query words over each item's title, body and comments."""
    docs = {n: collections.Counter(words(i["text"])) for n, i in items.items()}
    size = {n: sum(d.values()) for n, d in docs.items()}
    mean = sum(size.values()) / max(len(docs), 1)
    df = collections.Counter(w for d in docs.values() for w in d)
    scores = collections.Counter()
    for n, d in docs.items():
        for w in set(query):
            if d[w]:
                idf = math.log(1 + (len(docs) - df[w] + .5) / (df[w] + .5))
                scores[n] += idf * d[w] * 2.2 / (d[w] + 1.2 * (.25 + .75 * size[n] / mean))
    return scores


def path_scores(items, paths, before):
    """Pull requests whose commits touched each path, across renames, and the issues they closed."""
    scores = collections.Counter()
    for path in paths:
        log = run("git", "log", *(["--before", before] if before else []), "--follow", "--format=%s", "--", path)
        subjects = log.splitlines()
        for rank, subject in enumerate(subjects):
            for pr in map(int, re.findall(r"\(#(\d+)\)", subject)):
                for n in [pr, *items.get(pr, {}).get("closes", [])]:
                    scores[n] += PATH_WEIGHT / (1 + min(rank, len(subjects) - 1 - rank))
    return scores


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("words", nargs="*")
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--before")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    items = load(args.before)
    newest = max(items, default=1)
    scores = text_scores(items, words(" ".join(args.words))) + path_scores(items, args.path, args.before)
    for n in scores:
        scores[n] *= 1 + RECENT_GAIN * .5 ** ((newest - n) / RECENT_HALF_LIFE)
    ranked = [n for n, _ in scores.most_common() if n in items][:args.top]
    if not ranked:
        print("No earlier issue or pull request matches; widen the words or name a path.")
    for n in ranked:
        print(items[n]["head"])
        for record in items[n]["records"][:3]:
            print(f"  {record}")


main()

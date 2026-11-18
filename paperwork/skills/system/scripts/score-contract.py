#!/usr/bin/env python3
"""Score a contract against its sources both ways: how many rebuild questions it answers, and how many of its quoted values its sources hold.

usage: score-contract.py <contract> --root <subject root>

Prints `recall <answered> of <asked>` with each question left to a gap, `precision <found> of <quoted>` with each quote its record's
sources do not hold, and each source whose path is no file under the root; exit 1 when a quote or a path is missing, 0 otherwise.
A quote is a text between backticks, placeholders such as `<port>` left out of it, or a line of an item of the code form, in a record
that carries evidence; it is looked for in the whole text of the sources that record cites.
"""
import json
import pathlib
import re
import sys

QUOTE = re.compile(r"`([^`]+)`")
PLACEHOLDER = re.compile(r"<[^<>]*>")


def texts(value):
    """Each text inside VALUE, however deep."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for part in value.values():
            yield from texts(part)
    elif isinstance(value, list):
        for part in value:
            yield from texts(part)


def quotes(record):
    """The values RECORD quotes from the subject: each run of a backticked text between its placeholders."""
    found = []
    for text in texts({name: record[name] for name in ("label", "purpose", "statement", "info") if name in record}):
        for quote in QUOTE.findall(text):
            found += [part.strip() for part in PLACEHOLDER.split(quote) if len(part.strip()) > 1]
    return found


def score(contract, root):
    """The answered and asked counts, the open questions, the found and quoted counts, the missing quotes and the missing paths."""
    held, lost = {}, []
    for source in contract.get("sources", []):
        path = root / source["path"]
        if re.match(r"[a-z]+://", source["path"]):
            continue
        if path.is_file():
            held[source["id"]] = " ".join(path.read_text(errors="replace").split())
        else:
            lost.append(f"{source['id']}: {source['path']}")
    questions = contract.get("questions", [])
    gaps = [f"{question['id']}: {question['gap']}" for question in questions if not question.get("answers")]
    records = [element for kind in ("nodes", "edges", "areas") for element in contract.get(kind, [])]
    quoted, missing = 0, []
    for record in records + contract.get("properties", []):
        cited = [held[entry.split(":")[0]] for entry in record.get("evidence", []) if entry.split(":")[0] in held]
        for quote in quotes(record) if cited else ():
            quoted += 1
            if not any(" ".join(quote.split()) in text for text in cited):
                missing.append(f"{record['id']}: `{quote}`")
    return len(questions) - len(gaps), len(questions), gaps, quoted - len(missing), quoted, missing, lost


def main(args):
    if len(args) != 3 or args[1] != "--root" or args[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        contract = json.loads(pathlib.Path(args[0]).read_text())
        answered, asked, gaps, found, quoted, missing, lost = score(contract, pathlib.Path(args[2]))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        print(f"{args[0]}: {e!r}; run check-contract.py check on it first", file=sys.stderr)
        return 2
    print(f"recall {answered} of {asked}: rebuild questions the contract answers; each other is left to a gap")
    print("".join(f"  {line}\n" for line in gaps), end="")
    print(f"precision {found} of {quoted}: quoted values the cited sources hold; each other is wrong or cites the wrong source")
    print("".join(f"  {line}\n" for line in missing), end="")
    print("".join(f"missing path {line}\n" for line in lost), end="")
    return 1 if missing or lost else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

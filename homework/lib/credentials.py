"""Credential values and injected instructions in text, found by pattern so no model has to look.

A credential is recorded by name only: `redact` swaps each value for a marker that keeps the name."""
import re

REMOVED = "<credential removed>"
# a token starts at a word boundary, so a word like task-manager keeps its "sk-"
TOKEN = re.compile(r"\b(?:ghp_[A-Za-z0-9]{30,}|github_pat_\w{22,}|sk-ant-[\w-]{20,}|sk-[\w-]{20,}"
                   r"|xox[abposr]-[\w-]{10,}|AKIA[A-Z0-9]{16})")
BEARER = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}")
# a value of 8+ characters holding a digit, so a prose "token: the deploy token" stays; a variable ($NAME), a path and a date
# name a credential or hold none; a digit-free password is out of scope, since prose is not told from it
ASSIGNMENT = re.compile(r"(?i)\b((?:password|passwd|secret|api[_-]?key|token|credential)s?\s*[:=]\s*['\"]?)(?![$~/]|\d{4}-\d\d-\d\d)((?=[^\s'\"]*\d)[^\s'\"]{8,})")
KEY_BEGIN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
KEY_END = re.compile(r"-----END [A-Z ]*PRIVATE KEY-----")
FORBIDS = re.compile(r"(?i)\b(?:never|do not|don't|must not|should not|shall not)\s*$")
INJECTION = re.compile(
    r"(?i)\b(?:ignore|disregard|forget)\b[^.\n]{0,40}\b(?:previous|prior|above|earlier|your|all|any)\b[^.\n]{0,30}\binstructions?\b"
    r"|\b(?:reveal|send|leak|exfiltrate|print)\b[^.\n]{0,40}\b(?:secrets?|credentials?|api keys?|tokens?|passwords?|system prompt|private data)\b")


def redact(text):
    """The text with each credential value replaced, and a (line number, kind) per replacement."""
    found, out, in_key = [], [], False
    for number, line in enumerate(text.split("\n"), 1):
        if in_key:
            in_key = not KEY_END.search(line)
            continue
        if KEY_BEGIN.search(line):
            found.append((number, "private key"))
            out.append(KEY_BEGIN.sub(REMOVED, line))
            in_key = not KEY_END.search(line)
            continue
        for kind, pattern in (("token", TOKEN), ("bearer", BEARER)):
            line, count = pattern.subn(REMOVED, line)
            found += [(number, kind)] * count
        line, count = ASSIGNMENT.subn(lambda match: match.group(1) + REMOVED, line)
        found += [(number, "assignment")] * count
        out.append(line)
    return "\n".join(out), found


def injected(text):
    """The line numbers of lines that tell an agent to ignore its instructions or to reveal or send out secrets."""
    found = []
    for number, line in enumerate(text.split("\n"), 1):
        start = 0
        while match := INJECTION.search(line, start):
            # a rule whose negation stands right before the verb forbids the action, so it is no injection
            if not FORBIDS.search(" ".join(line[:match.start()].split()[-2:]) + " "):
                found.append(number)
                break
            start = match.start() + 1  # a later verb in the same line may stand alone
    return found

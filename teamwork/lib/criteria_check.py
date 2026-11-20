"""How a `[check]` criterion reads: the command it runs, the output it expects, the one value it quotes for the base.
run-criteria.py runs a check by it and check-criteria.py refuses a check it cannot read, so both share this one parse."""
import pathlib
import re
import shlex

import task_state

# the number of the task that added the Goal path check, so every Goal written before it keeps its old rules
GOAL_CUT_OFF = 1305
PATH_LINE = re.compile(r"^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?Path(?:\*\*)?:(?:\*\*)?[ \t]*(.*)$", re.M | re.I)
# the blanks of the form FIX prints, which a writer who copies it unfilled has not answered
BLANK = re.compile(r"<(?:caller|step before|step after|who sees the result)>")
# the relations Scope the path names between a changed part and its flow, each written `label: who or what`
RELATION = re.compile(r"^\s*(?:caller|before|after|meets)\s*:\s*(\S.*?)\s*$", re.I)
# a value that opens by saying there is no such party, not a party, unless a party follows `but` or `except`
NOBODY = re.compile(r"^(?:none|no one|nobody|nothing|no\s|n/a|unknown|tbd|-)(?!.*\b(?:but|except)\b)", re.I)

GOAL_FIX = {
    "no path in the Goal": "add to the Goal one line, `Path: caller: <caller>; before: <step before>; after: <step after>; meets: <who sees the result>`, "
                           "naming the flow of the changed part, as protocol.md's **Scope the path** says: its callers, the steps before and after it, "
                           "and whoever meets its result, all on that one line; a Goal that names only the changed part misses what breaks when it changes",
    "path names no flow": "as protocol.md's **Scope the path** says, write the `Path:` line as `label: name` items split by `;`, the only form that counts: at least one of "
                          "`caller:`, `before:`, `after:` or `meets:` followed by the party it names, never `none`, empty, or a `<...>` blank of the form left in the line; "
                          "a line that names only the changed part, or says nothing is affected, gives no flow",
}


def goal_defects(goal):
    """The defects of a Goal's `Path:` line: absent, or present and naming no flow of the changed part."""
    lines = [text.strip() for text in PATH_LINE.findall(goal)]
    if not any(lines):
        return ["no path in the Goal"]
    items = [RELATION.match(item) for text in lines for item in text.split(";")]
    named = [item.group(1) for item in items if item]
    return [] if named and not any(BLANK.search(text) for text in lines) and any(not NOBODY.match(value) for value in named) else ["path names no flow"]


PLACEHOLDER = re.compile(r"<[A-Za-z][\w .-]*>")
# a code span, or an empty one, which SPAN skips
# an empty one only where the clause goes on to its end, so a padded `` echo `x` `` stays one span
SPANS = re.compile(r"(?<!`)``(?=\s*(?:$|[;.,)]|\bon\b|\bwhen\b))|" + task_state.SPAN.pattern)
# a remark in parentheses is hidden too, since it may hold a `,` or `;`
HIDDEN = re.compile(SPANS.pattern + r"|\([^()]*\)")
NOTE = re.compile(r"\s*\0(\d+)\0$")


def hide(text):
    """(text with each code span a token no clause split matches inside, the spans), so a `when` or `;` in a quoted value never splits."""
    kept = []

    def stash(match):
        kept.append(match.group())
        return f"\0{len(kept) - 1}\0"
    return HIDDEN.sub(stash, text), kept


def show(text, kept):
    return re.sub(r"\0(\d+)\0", lambda match: kept[int(match.group(1))], text)


def is_remark(text):
    """A parenthesis that only explains; one with a code span or an `or` may add a second accepted value, so it stays."""
    return text.lstrip().startswith("(") and "`" not in text and not re.search(r"\bor\b", text)


def clause_of(rest):
    """(first clause of text after `prints` or `on base` with a remark in parentheses cut, the hidden text after it, the hidden spans)."""
    hidden, kept = hide(rest)
    clause, *parts = re.split(r"([;.](?:\s|$)|,\s+(?!\0)|\bwhen\b|\bon (?:base|main)\b)", hidden)
    clause = clause.strip()
    while (note := NOTE.search(clause)) and is_remark(kept[int(note.group(1))]):
        clause = clause[:note.start()]
    return show(clause, kept).strip(), "".join(parts), kept


def expectation(detail):
    """(command, test) of a `[check]`'s details, test ('prints', text), ('more', n), ('exits', n) or (None, why) when undecidable."""
    spans = list(SPANS.finditer(detail))
    if not spans or spans[0].group(2) is None:
        return None, (None, "no command")
    command, after = spans[0].group(2), detail[spans[0].end():]
    if detail[:spans[0].start()].strip():
        return command, (None, "words before the command")
    verb = re.search(r"\b(prints|exits)\b", after)
    if not verb or any(other.start() < spans[0].end() + verb.start() for other in spans[1:]):
        return command, (None, "two commands" if verb else "no prints or exits")
    if PLACEHOLDER.search(command) or "..." in command or "…" in command:
        return command, (None, "placeholder in the command")
    rest = after[verb.end():]
    # the expected text runs to the clause's end, so a second value such as `a` then `b` or `a`, `b` reads as undecidable
    clause, after_clause, kept = clause_of(rest)
    # a further command before the base's output is a second condition, which this value alone would pass; a `when` explains
    tail = re.split(r"\bon (?:base|main)\b", after_clause)[0]
    tail = show(re.sub(r"\bwhen\b.*?(?:[;.](?:\s|$)|$)", "", tail, flags=re.S), kept)
    if re.match(r"[,;]\s*and\b", tail) or any(re.search(r"\s", match.group(2)) for match in task_state.SPAN.finditer(tail)):
        return command, (None, "more than one condition")
    if verb.group(1) == "exits":
        code = re.fullmatch(r"`?(\d+)`?", clause)
        return command, ("exits", int(code.group(1))) if code else (None, "expected status not one value")
    found = list(task_state.SPAN.finditer(clause))
    span = found[0] if len(found) == 1 and found[0].span() == (0, len(clause)) else None
    more = re.fullmatch(r"`?(\d+)`? or more", clause)
    if clause == "nothing":
        return command, ("prints", "")
    if more:
        return command, ("more", int(more.group(1)))
    if clause == "``":
        return command, ("prints", "")
    if span and not PLACEHOLDER.search(span.group(2)):
        return command, ("prints", span.group(2))
    if re.fullmatch(r"[\w-]+", clause):
        return command, ("prints", clause)
    return command, (None, "expected output not one value")


def base_quote(detail):
    """The one value quoted after `on base` in a `[check]`'s details, or None when it is not one value."""
    # tasks filed before the base was named quote `on main`
    hidden, kept = hide(detail)
    _, found, rest = (re.split(r"\b(on (?:base|main))\b", hidden, maxsplit=1) + ["", ""])[:3]
    clause = clause_of(show(rest, kept))[0]
    clause = re.sub(r"^(?:it\s+)?prints\s+", "", clause)
    spans = list(task_state.SPAN.finditer(clause))
    if len(spans) == 1 and spans[0].span() == (0, len(clause)):
        return spans[0].group(2)
    if clause in ("nothing", "``"):
        return ""
    return clause if found and re.fullmatch(r"[\w-]+", clause) else None


def unreadable(detail):
    """Why run-criteria.py cannot decide a `[check]`'s details at the head or on the base, or None when it can."""
    _, test = expectation(detail)
    if test[0] is None:
        return test[1]
    if test[0] == "prints" and base_quote(detail) is None:
        return "no one value after `on base`"
    return None


def verdict(test, status, out):
    """`pass`, `fail`, or `unclear` for a `prints` text found only among other lines, which a judge reads, of a run's STATUS and OUT against TEST."""
    kind, want = test
    if status is None:
        return "fail"
    if kind == "exits":
        return "pass" if status == want else "fail"
    if kind == "more":
        first = out.split(maxsplit=1)[:1]
        return "pass" if first and first[0].isdigit() and int(first[0]) >= want else "fail"
    if out == want:
        return "pass"
    return "unclear" if want and re.search(rf"(?<!\w){re.escape(want)}(?!\w)", out) else "fail"


# outside quotes only these may precede the first pipe; anything else (`;`, `&`, `{`, `(`, `#`, a backslash, ...) might hide a pipe or a stage
SAFE = re.compile(r"[\w \t./=:,+@%~<-]|\$\w|\$(?=[\"'])")
# a compound command owns the pipe that follows its first word, so the pipe is not a stage boundary
COMPOUND = {"if", "while", "until", "for", "case", "select", "time", "function", "coproc"}


def after_first_pipe(command):
    """The command without its first pipe stage, split at the first `|` outside quotes, or None when the split is not certain:
    no pipe, or before it a character outside SAFE, or in double quotes a `$(`, `${`, backtick or backslash, which
    could hide a pipe or drop part of the first stage."""
    if command.split(None, 1)[:1] and command.split(None, 1)[0] in COMPOUND:
        return None
    quote, i = None, 0
    while i < len(command):
        char = command[i]
        if char == "\\":
            return None
        if quote:
            # a substitution inside double quotes can hold quotes of its own, which end this quote early
            if quote == '"' and (char == "`" or command[i:i + 2] in ("$(", "${")):
                return None
            quote = None if char == quote else quote
        elif char in "'\"":
            quote = char
        elif char == "|" and command[i:i + 2] != "||":
            return command[i + 1:]
        elif not (match := SAFE.match(command, i)):
            return None
        else:
            i = match.end() - 1
        i += 1
    return None


# a program `claude` run with `-p` or `--print` starts a live session
SESSION = re.compile(r"(?<![\w\"'.-])claude(?![\w-])[^|;&\n]*?\s(?:-p|--print)\b")
WATCHES = re.compile(r"\bwatches:\s*([^;`]*?)(?=\s+on (?:base|main)\b|;|\.(?:\s|$)|$)")


def starts_session(command):
    return bool(SESSION.search(command))


# flags of `claude` that take several values, so a prompt after one is read as one more value
VARIADIC = {"--allowedTools", "--allowed-tools", "--disallowedTools", "--disallowed-tools", "--tools", "--add-dir", "--mcp-config", "--betas", "--file"}
# flags of `claude` that take one value, which is no prompt
SINGLE = {"--model", "--output-format", "--input-format", "--max-turns", "--permission-mode", "--append-system-prompt", "--system-prompt", "--resume", "--session-id", "--settings", "--agent", "--fallback-model", "--plugin-dir", "--effort", "--name", "-n", "-r", "-c"}


def swallowed_flag(command):
    """The variadic flag of the `claude -p` stage whose run of values holds the prompt, else None: a variadic flag reads every word up to the next flag or `--`,
    so with a word in its run and no prompt before it, the prompt is one of its values; a stage that ends in a bare `--` with no prompt before it has none, and gives `--`."""
    first = command if (rest := after_first_pipe(command)) is None else command[:len(command) - len(rest) - 1]
    if not starts_session(first):
        return None
    try:
        words = shlex.split(first)
    except ValueError:
        return None
    flag, prompted, found, values, i = None, False, None, 0, words.index("claude") + 1 if "claude" in words else 0
    skip = False
    for at, word in enumerate(words[i:], i):
        if skip:
            skip = False
            continue
        if word == "--":
            return "--" if at == len(words) - 1 and not prompted else None
        if word.startswith("-"):
            found = found or (flag if flag and values > 0 else None)
            flag, values = (word, 0) if word in VARIADIC else (None, 0)
            skip = word in SINGLE
        elif flag:
            values += 1
        else:
            prompted = True
    found = found or (flag if flag and values > 0 else None)
    return None if prompted else found


def watched(detail):
    """The paths a `[check]` says its live run depends on, after `watches:`, as the files and folders that decide whether a saved transcript still holds."""
    found = WATCHES.search(re.sub(SPANS, "", detail))
    return found.group(1).split() if found else []


def live_stage(detail):
    """(first stage, the stages after it) of a `[check]` whose first pipe stage starts a live session and which names what it `watches:`, else None;
    the first stage's output is the transcript the later stages judge, so a fix to them replays it."""
    command, _ = expectation(detail)
    rest = after_first_pipe(command) if command else None
    if rest is None or not watched(detail):
        return None
    first = command[:len(command) - len(rest) - 1]
    return (first.strip(), rest) if starts_session(first) else None


NEXT_WORD = r"[^A-Za-z0-9-]+([A-Za-z0-9-]+)"  # the word after a marker such as `prints`
# the first task number filed after the commit that wrote this line, so every task filed before keeps its old rules
CUT_OFF = 1195
MOST = 5
# programs that only read or reshape text, so a check made of them alone never runs the system it judges
SCANS = {"grep", "egrep", "fgrep", "rg", "ag", "awk", "gawk", "sed", "cat", "head", "tail", "wc", "sort", "uniq",
         "cut", "tr", "test", "[", "diff", "cmp", "jq", "echo", "printf", "true", "false"}
INLINE = {"python": "-c", "python3": "-c", "node": "-e", "perl": "-e", "ruby": "-e"}
SHELLS = {"sh", "bash", "zsh"}
# inline code that starts a process runs the system; any other inline code only reads
RUNS = re.compile(r"\b(?:subprocess|os\.system|os\.popen|os\.exec\w*|child_process|system\s*\()")
# wrappers that run the command after them, so the command decides
WRAPPERS = {"env", "command", "exec", "nice", "nohup", "time", "timeout", "xargs"}


FIX = {
    "prompt swallowed": "put the prompt first or after `--`, since a flag that takes several values reads the prompt as one more value and `claude` exits with Input must be provided",
    "no prompt after --": "put the prompt after the `--`, since a `--` that ends the command leaves `claude` no prompt and it exits with Input must be provided",
    "no kind": "open the criterion with `[check]` or `[score]` before its name",
    "no name": "put a bold name after the kind: `[check] **<name>**: <details>`",
    "no command": "write the command that decides in a code span; a `[check]` is a command whose output decides",
    "no base output": "quote, after `on base`, the failing output of the same command on the base, as in "
                      "`prints ok; on base nothing`",
    "passes on base": "the word after `prints` equals the word after `on base`, so the check passes on the base; "
                      "quote the output it gives there, which must differ",
    "words before the command": "start the details with the command in a code span; move any note after the expected output",
    "two commands": "keep one command in a code span before `prints`; a second code span there makes it ambiguous",
    "no prints or exits": "say `prints <output>` or `exits <status>` after the command",
    "placeholder in the command": "write the command as run, with no `<word>` in it",
    "more than one condition": "split a second condition into its own criterion",
    "expected status not one value": "write one status number after `exits`",
    "expected output not one value": "write one value after `prints`, in a code span or one word",
    "no one value after `on base`": "quote one value after `on base`, in a code span or one word",
    "elided command": "write the whole command; `...` or `…` in the code span cannot be run",
    "no sample": "name the sample with `sample:`",
    "no rubric": "name the rubric with `rubric:`",
    "no base measure": "state the base's measure on the sample, with the word `base`",
    "more than 5 criteria": "keep one criterion per outcome, at most 5; group clauses that one outcome covers",
    "not a scenario": "make the check a scenario that runs the system and prints `PASS`, and quote `FAIL` on base",
    "live stage not replayable": "make the first pipe stage the only `claude -p` run, with no redirect, subshell or `&&` before the pipe, "
                                 "and name the paths it runs against: `watches: <path>...`; the stages after it judge its saved transcript",
    **GOAL_FIX,
    "text scan": "run the system and judge its behaviour; a grep, `awk` or file read alone checks words, not what works",
    "whole repository check": "run the fixture runners the change touches; the whole check runs once, at the head before the judge, as worker.md's Land says",
}


def stages(command):
    """The words of each simple command in a shell line, split at `|`, `&&`, `||`, `;` and newlines."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    stage = []
    try:
        for token in lexer:
            if token and set(token) <= set("|&;()\n"):
                if stage:
                    yield stage
                stage = []
            else:
                stage.append(token)
    except ValueError:
        stage = command.split()
    if stage:
        yield stage


def scans_only(command):
    """True when every simple command in COMMAND only reads text, so the check runs nothing of the system."""
    for words in stages(command):
        while words and (re.fullmatch(r"\w+=.*|-\w.*|\d+[smhd]?", words[0]) or pathlib.PurePath(words[0]).name in WRAPPERS):
            words = words[1:]
        if not words:
            continue
        program = pathlib.PurePath(words[0]).name
        if program in SHELLS and "-c" in words[1:-1]:
            if not scans_only(words[words.index("-c") + 1]):
                return False
        elif program in INLINE and INLINE[program] in words[1:-1]:
            if RUNS.search(words[words.index(INLINE[program]) + 1]):
                return False
        elif program not in SCANS:
            return False
    return True


def without_scans(command):
    """COMMAND as bash text that runs each text-scan program not reading a pipe as a command that does nothing and succeeds, so what remains decides the check; None when it starts a session."""
    if starts_session(command):
        return None
    names = [name for name in SCANS if name not in ("echo", "printf", "true", "false", "test", "[")]  # a test judges a value the system printed
    functions = "".join(f'{name}() {{ if builtin test -p /dev/stdin; then command {name} "$@"; else true; fi; }}; ' for name in names)
    return "exec </dev/null; " + functions + command


def runs_whole_check(command):
    """True when a simple command in COMMAND, or in a shell's `-c` text or inline code, runs `check-repository.py`; a mention inside another quoted word, such as a
    sample body, runs nothing."""
    for words in stages(command):
        if any(pathlib.PurePath(word).name == "check-repository.py" for word in words):
            return True
        program = pathlib.PurePath(words[0]).name if words else ""
        # a bundle such as `-lc` or `-ec` ends in the `-c` whose next word is the text the shell runs
        texts = [words[i + 1] for i, word in enumerate(words[1:-1], 1) if program in SHELLS and re.fullmatch(r"-[a-z]*c", word)
                 or program in INLINE and word == INLINE[program]]
        if any("check-repository.py" in text if program in INLINE else runs_whole_check(text) for text in texts):
            return True
    return False


def scenario_defects(kind, detail):
    """The defects a task at or above the cut-off adds: a `[check]` that is no PASS/FAIL scenario, runs the whole repository check, or is only a text scan."""
    if kind != "check":
        return []
    command, test = expectation(detail)
    if command is None:
        return []
    found = [] if test == ("prints", "PASS") and base_quote(detail) == "FAIL" else ["not a scenario"]
    found += ["whole repository check"] if runs_whole_check(command) else []
    return found + (["text scan"] if scans_only(command) else [])


def live_defects(kind, detail):
    """A `[check]` that starts a session anywhere but a first stage that run-criteria.py can save and replay, which would start a session on each run."""
    command, _ = expectation(detail)
    return ["live stage not replayable"] if kind == "check" and command and starts_session(command) and not live_stage(detail) else []


def order_defects(kind, detail):
    """A live `[check]` whose prompt follows a flag that takes values, which `claude` reads as one more value, or whose command ends in a bare `--`, and `claude` then exits with "Input must be provided"."""
    command, _ = expectation(detail)
    flag = swallowed_flag(command) if kind == "check" and command else None
    if flag == "--":
        return ["no prompt after --"]
    return [f"prompt swallowed by {flag}"] if flag else []


def defects(kind, name, detail):
    """The defects of one criterion, in the order the task lists them."""
    found = [] if kind in ("check", "score") else ["no kind"]
    found += [] if name else ["no name"]
    span = task_state.SPAN.search(detail)
    rest = detail[:span.start()] + detail[span.end():] if span else detail
    if kind == "check":
        # tasks filed before the base was named quote `on main`
        passes, base = re.search(r"\bprints" + NEXT_WORD, rest), re.search(r"\bon (?:base|main)" + NEXT_WORD, rest)
        found += [] if span else ["no command"]
        found += ["no base output"] if not base else ["passes on base"] if passes and passes.group(1) == base.group(1) else []
    # what run-criteria.py cannot read; lint already names an elided command, and a missing base output covers the quote
    why = unreadable(detail) if kind == "check" and span else None
    elided = bool(span) and ("..." in span.group(2) or "…" in span.group(2))
    covered = why in found or elided and why == "placeholder in the command" or "no base output" in found and why and why.endswith("`on base`")
    found += [why] if why and not covered else []
    if elided:
        found.append("elided command")
    if kind == "score":
        found += [f"no {word}" for word in ("sample", "rubric") if f"{word}:" not in rest]
        found += [] if re.search(r"\b(?:base|main)\b", rest) else ["no base measure"]
    return found


def lint(body, task=None):
    """[(position, key, defects)] of BODY's Goal and criteria, as check-criteria.py prints them, key naming what holds the defects so an old body's can be told from a new one's."""
    lines = task_state.ITEM.findall(task_state.sections(body).get("done", ""))
    new_rules = task is None or task >= CUT_OFF
    goal = task_state.sections(body).get("goal")
    goal_found = goal_defects(goal) if goal is not None and (task is None or task >= GOAL_CUT_OFF) else []
    # a part, `[task] #n`, is no criterion, so its form is the graph's to check
    matched = [(line_number, line, task_state.CRITERION.match(line).groups()[1:]) for line_number, line in enumerate(lines, 1)]
    criteria = [(line_number, line, groups) for line_number, line, groups in matched if groups[0] != "task"]
    flagged = [(line_number, " ".join(line.split()), found) for line_number, line, groups in criteria
               for found in [defects(*groups) + (scenario_defects(groups[0], groups[2]) + live_defects(groups[0], groups[2]) + order_defects(groups[0], groups[2]) if new_rules else [])] if found]
    if new_rules and len(criteria) > MOST:
        flagged.insert(0, ("body", "body", ["more than 5 criteria"]))
    return ([("goal", "goal", goal_found)] if goal_found else []) + flagged


def body_refusals(body, number=None, old=""):
    """The sentences, each ending in its fix, that refuse BODY for what check-criteria.py prints on it, none for a defect OLD already held, so an edit to some other part is never blocked."""
    held = {(key, name) for _, key, found in lint(old, number) for name in found}
    return [f"{position}: {name}: {FIX[name.split(' by ')[0]]}" for position, key, found in lint(body, number) for name in found if (key, name) not in held]

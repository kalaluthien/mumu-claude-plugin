#!/usr/bin/env python3
"""Route each hook event to its role's timing-bound steps, kept in this hook instead of in the playbooks.

usage: route-event.py
It reads one hook event as JSON on stdin and prints the hook's answer, if any, as JSON on stdout."""
import json
import os
import pathlib
import re
import shlex
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import background_work  # noqa: E402
import board  # noqa: E402
import install_line  # noqa: E402
import session  # noqa: E402
import team_gaps  # noqa: E402
import team_names  # noqa: E402

PLAYBOOKS = ROOT / "skills" / "kick-off" / "references"
GRAMMAR = PLAYBOOKS / "issue-grammar.md"
# the rules are found in the playbooks at each call, never copied here, so a playbook edit cannot leave a stale reminder
NO_DATA = "A text never carries data"
REMINDED = {"file": ("`file`", "40 characters", NO_DATA), "change": ("40 characters",), "comment": ("**Comment**", "`comment`", NO_DATA), "change comment": ("**Comment**",),
            "resolve": ("`resolve`", NO_DATA), "edit": ("edit-issue-body", "40 characters"), "change edit": ("40 characters",)}
WORKTREES = "/.claude/worktrees/"
# the only commands whose rewrite is offered: reads, so the live checkout is never written by a command the hook suggests
READ_GIT = {"status", "log", "diff", "show", "grep", "ls-files", "rev-parse", "blame", "describe", "shortlog", "cat-file", "ls-tree", "for-each-ref", "ls-remote", "merge-base", "rev-list", "show-ref"}
# each read and the option letters it may take, since any other letter may write a file, take a file or take an operand that is no path
READ_ONLY = {"cat": "nbsAETtuv", "head": "ncqv", "tail": "ncqv", "wc": "lwcmL", "ls": "lahtrSd1FAGikpsuUcRn", "grep": "ivnclLhHwxEFsqrRaIzbmABCo", "rg": "ivnclhHwxFsSuUzoABC",
             "stat": "L", "file": "bLiIzk", "du": "ahskcxHL", "cut": "cfdbsn", "tr": "cdsC", "diff": "uUqrNbBwicy", "nl": "abfhinpstvw", "tree": "adfilnpstuCDFNQ", "sed": "nErsz"}
PATTERN_FIRST = {"grep", "rg", "sed"}
# the option letters that take the next word as their value, which is no path
TAKES_VALUE = {"head": "nc", "tail": "nc", "grep": "mABC", "rg": "ABC", "cut": "bcdf", "nl": "bfhinpsvw", "diff": "U"}
# a read that takes the folder it stands in when it is given none
DEFAULT_FOLDER = {"ls", "du", "tree"}
# commands that name no file of the checkout, and the reads of `gh`, which asks GitHub about the repository the worktree shares
NO_FILES = {"echo", "printf"}
GH_READS = {("issue", "view"), ("issue", "list"), ("pr", "view"), ("pr", "list"), ("pr", "diff"), ("pr", "checks")}
# the reads that pick their target from the branch of the folder they run in unless given a number or a url
GH_NEEDS_TARGET = {("issue", "view"), ("pr", "view"), ("pr", "diff"), ("pr", "checks")}
# a read whose operands are no file: it reads standard input
STDIN_ONLY = {"tr"}
# reads that print the name of each operand they are given, which the rewrite makes an absolute path, so they are refused with an operand of the folder
NAME_PRINTERS = {"wc", "du", "file", "stat", "diff", "tree"}
# the option letters that make a read print the name of each operand
NAME_OPTIONS = {"head": "v", "tail": "v", "grep": "lLHrR", "rg": "lH", "ls": "dR"}
# interpreters whose script operand is a read; any option beyond these takes code or a module
SCRIPT_RUNNERS = {"python3", "python", "bash", "sh", "node"}
# the long options that hand git a program to run or a file to write; git takes any prefix of a long option, so a prefix of one is refused too
GIT_LONG_WRITES = ("output", "open-files-in-pager", "upload-pack", "exec")
GIT_VALUE_LETTERS = "SGeABCULM"
# a `gh api` short flag, bundled or with its value attached, that sets a field or a method
API_SHORT_WRITES = re.compile(r"-[A-Za-z]*[fFX]")
# a sed script a read can take: statements apart by `;`, each an optional address range, then print, delete, quit or a substitution with no `w` or `e` flag
SED_STATEMENT = r"(?:(?:\d+|\$|/[^/\\[\\\\]*/)(?:,(?:\d+|\$|/[^/\\[\\\\]*/))?)?(?:[pdq]|s/[^/\\[\\\\]*/[^/\\[\\\\]*/[gpiI0-9]*)"
SED_READ = re.compile(rf"{SED_STATEMENT}(?:;{SED_STATEMENT})*;?")
# one addressed print, delete or quit, whose address may hold a bracket expression since nothing follows it that a bracket could hide
SED_ADDRESSED = re.compile(r"(?:/[^/\\]*/|\d+|\$)(?:,(?:/[^/\\]*/|\d+|\$))?[pdq]")
# a write to a GitHub issue, by `gh issue` or by `gh api` with a body, a method that writes or a GraphQL issue or comment mutation. A `gh`, shell or `eval`
# word runs when it opens a simple command or follows only words that are no NEVER_RUNS word, such as a wrapper and its flags, read in a text with its
# quoted strings, substitutions, comments and heredoc bodies blanked, since a commit message, a grep pattern or a note may name it; what it is given is read
# unblanked. A shell or `eval` runs its `-c` code or its words, else the heredoc or here-string it reads and the text a pipe feeds it; a command
# substitution runs its inside. A reminder against a habit, not a wall: a command a variable, a function, a group or a script file names is not followed.
# a word that runs none of the words after it, so a command word behind it is a mention
NEVER_RUNS = r"in|echo|printf|grep|egrep|fgrep|rg|git|cat|tee|ls|head|tail|wc|man|which|type|test|tr|cut|sort|uniq|jq|nl|diff|less"
WORD_START = rf"(?:^|[;&|(){{`!\n])[ \t]*(?:(?!(?:\S*/)?(?:{NEVER_RUNS})[ \t])[^\s;&|()<>]+[ \t]+)*?(?:\S*/)?"
COMMAND_START = WORD_START + r"gh\s+(?:-{1,2}\w[\w-]*(?:[\s=][^\s-]\S*)?\s+)*"
GITHUB_ISSUE_WRITE = re.compile(COMMAND_START + r"issue\s+(?:-{1,2}\w[\w-]*(?:[\s=][^\s-]\S*)?\s+)*"
                                r"(?:create|new|comment|edit|close|reopen|delete|transfer|pin|unpin|lock|unlock|develop)\b", re.M)
GITHUB_API = re.compile(COMMAND_START + r"api\s+(?!graphql)", re.M)
GITHUB_GRAPHQL = re.compile(COMMAND_START + r"api\s+graphql\b", re.M)
API_WRITES = re.compile(r"(?:^|(?<=\s))(?:(?:-X|--method)[\s=]*(?:POST|PATCH|PUT|DELETE)\b|-[fF]\b|--(?:raw-)?field\b|--input\b)")
API_READS = re.compile(r"(?:^|(?<=\s))(?:-X|--method)[\s=]*GET\b")
API_ISSUES = re.compile(r"\b(?:issues|sub_issues|dependencies)\b")
API_FIELD_VALUE = re.compile(r"(?:^|(?<=\s))(?:-[fF]|--(?:raw-)?field)[\s=]*(?:(?:[^\s\"']*(?:\"(?:\\.|[^\"\\])*\"|'[^']*'))+[^\s\"']*|\S+)")
SHELL_START = re.compile(WORD_START + r"((?:r?ba|da|z|k|mk|pdk|tc|c|y|o|a)?sh(?:-?[\d.]+)?|fish|nu|rc|pwsh|eval)(?![\w.-])", re.M)
PIPELINE_START = re.compile(r";|&&|\|\||(?<![|<>&])&(?![&>])|(?<![|&][ \t])(?<![|&])\n")
LOOSE_WRITE = re.compile(r"(?:\b|(?<=\\[nt]))gh\b[^\n]*?\b(?:issue\b[^\n]*?\b(?:create|new|comment|edit|close|reopen|delete|transfer|pin|unpin|lock|unlock|develop)\b"
                         r"|api\b[^\n]*?(?:(?:-X|--method)[\s=]*(?:POST|PATCH|PUT|DELETE)\b|(?<!\S)-[fF]\b|--(?:raw-)?field\b|--input\b|\bmutation\b))")
SUBSTITUTION = re.compile(r"(?<!\\)\$\(((?:[^()]|\([^()]*\))*)\)|(?<!\\)`((?:\\.|[^`\\])*)`")
HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)\\?(\w+)\1[^\n]*\n(.*?)\n[ \t]*\2[ \t]*(?=\n|$)", re.S)
HERE_STRING = re.compile(r"<<<[ \t]*(\"(?:\\.|[^\"\\])*\"|'[^']*'|(?:\\.|[^\s\\])+)")
QUOTED = re.compile(r"\"(?:\\.|[^\"\\])*\"|'[^']*'")
COMMENT = re.compile(r"(?:^|(?<=[ \t;&|(]))#[^\n]*", re.M)
STAGE_JOINT = re.compile(r"&&|\|\||[;|\n]|(?<![<>])&(?![>&])")
PASSED_REDIRECT = re.compile(r"(?:\d*|&)>(?:&\d+|/dev/null)")
JOINTS = {"&&": "&&", "||": "||", ";": ";", "\n": ";", "|": "|"}
CHANGE_DIRECTORY = re.compile(r"(?:^|[;&|({]|\bthen|\bdo)[ \t]*(?:cd|pushd)[ \t]+(?:--[ \t]+)?(\"[^\"]*\"|'[^']*'|[^\s;&|)}]+)", re.M)


def blanked_bodies(command):
    """COMMAND of the same length with each heredoc body turned into `_`."""
    return HEREDOC.sub(lambda found: found.group(0).partition("\n")[0] + "\n" + "_" * (len(found.group(0)) - len(found.group(0).partition("\n")[0]) - 1), command)


def blank_inside(found, opening):
    """The text FOUND matched, kept for its OPENING characters and its last one, and `_` between."""
    return found.group(0)[:opening] + "_" * (len(found.group(0)) - opening - 1) + found.group(0)[-1]


def blank_text(command):
    """COMMAND of the same length with each heredoc body, command substitution's, quoted string's inside and comment turned into `_`, so a word inside
    them is no command and a quote inside a substitution closes none outside it; a substitution is read by itself."""
    command = SUBSTITUTION.sub(lambda found: blank_inside(found, 2 if found.group(0)[0] == "$" else 1), blanked_bodies(command))
    command = QUOTED.sub(lambda found: blank_inside(found, 1), command)
    return COMMENT.sub(lambda found: "_" * len(found.group(0)), command)


def inert_text(command):
    """COMMAND of the same length with each heredoc body, comment and quoted string turned into `_`, except a `$(...)` the shell runs, even inside double quotes,
    so a cd in it is read as a command and a cd in plain text is not."""
    def blank_quoted(found):
        text, kept = found.group(0), set()
        for substitution in SUBSTITUTION.finditer(text) if text[0] == '"' else ():
            if text[substitution.start()] == "$":
                kept.update(range(*substitution.span()))
        return "".join(char if at in kept or at in (0, len(text) - 1) else "_" for at, char in enumerate(text))
    return COMMENT.sub(lambda found: "_" * len(found.group(0)), QUOTED.sub(blank_quoted, blanked_bodies(command)))


def rest_of_command(command, blanked, start):
    """The text of COMMAND from START to the end of its simple command, found in the blanked text, so a `;` inside a quoted body ends nothing."""
    end = re.search(r"[;|\n]|(?<![<>])&(?!>)", blanked[start:])
    return command[start:start + end.start()] if end else command[start:]


def unquoted(word):
    """WORD as the shell hands it on, its quotes removed, or as written when they never close."""
    try:
        return " ".join(shlex.split(word))
    except ValueError:
        return word


def shell_writes(command, blanked, found):
    """Whether the shell or `eval` FOUND in BLANKED, the blanked COMMAND, writes to a GitHub issue: by its `-c` code or by the words `eval` runs; else, when
    it reads its input rather than a script file, by the heredoc or here-string it reads, or by a write in the text the stages before it in its pipeline
    print, since that text is what it runs."""
    rest = rest_of_command(command, blanked, found.end())
    lexer = shlex.shlex(rest, posix=True, punctuation_chars="<>&()")
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return bool(LOOSE_WRITE.search(rest))
    redirect = [bool(token) and set(token) <= set("<>&") for token in tokens] + [False]
    words = [token for at, token in enumerate(tokens) if not redirect[at] and not (at and redirect[at - 1]) and not (token.isdigit() and redirect[at + 1])
             and token.strip("()")]
    if found.group(1) == "eval":
        return writes_github_issue(" ".join(words[words[:1] == ["--"]:]))
    for at, option in enumerate(words):
        if option.startswith("--command="):
            return writes_github_issue(option.partition("=")[2])
        if option in ("--command", "-Command") or option[:1] == "-" and option[1:2] != "-" and "c" in option[1:]:
            return writes_github_issue(next((word for word in words[at + 1:] if not word.startswith("-")), ""))
    operand = 0
    while operand < len(words) and words[operand][:1] in "-+" and words[operand] not in ("-", "--"):
        operand += 2 if words[operand][1:2] != "-" and words[operand][-1] in "oO" else 1
    if "--version" in words[:operand] or "--help" in words[:operand] or words[operand:] and words[operand] not in ("-", "--", "/dev/stdin", "/dev/fd/0"):
        return False
    end = found.end() + len(rest)
    start = max((match.end() for match in PIPELINE_START.finditer(blanked, 0, found.start() + 1)), default=0)
    fed = [HEREDOC, HERE_STRING]
    own = [match for pattern in fed for match in pattern.finditer(command) if found.end() <= match.start() < end]
    before = [match for pattern in fed for match in pattern.finditer(command) if start <= match.start() < found.start()]
    return any(writes_github_issue(match.group(3) if match.re is HEREDOC else unquoted(match.group(1))) for match in own) or bool(
        LOOSE_WRITE.search("\n".join([command[start:found.start()]] + [match.group(match.lastindex) for match in before])))


def writes_github_issue(command):
    """True when COMMAND, a shell or `eval` it runs, or a command substitution it runs, writes to a GitHub issue."""
    command = command.replace("\\\n", " ")
    blanked = blank_text(command)
    if GITHUB_ISSUE_WRITE.search(blanked):
        return True
    for found in GITHUB_API.finditer(blanked):
        rest = rest_of_command(command, blanked, found.end())
        if API_WRITES.search(rest) and not API_READS.search(rest) and API_ISSUES.search(API_FIELD_VALUE.sub(" ", rest)):
            return True
    for found in GITHUB_GRAPHQL.finditer(blanked):
        if re.search(r"\bmutation\b.*(?:[Ii]ssue|[Cc]omment)", rest_of_command(command, blanked, found.end()), re.S):
            return True
    if any(shell_writes(command, blanked, found) for found in SHELL_START.finditer(blanked)):
        return True
    unrun = re.sub(r"'[^']*'", lambda found: "'" + "_" * (len(found.group(0)) - 2) + "'", blanked_bodies(command))
    return any(writes_github_issue(command[found.start(1):found.end(1)] if found.group(1) is not None else command[found.start(2):found.end(2)])
               for found in SUBSTITUTION.finditer(unrun))


def directory_before(prefix, cwd):
    """The folder a command written after PREFIX starts in: CWD moved by each `cd` of PREFIX that a `&&`, `;` or `(` carries on to it, and CWD again after any
    other joint, since a pipe, `||`, `&` or a closed subshell leaves the folder as it was."""
    try:
        tokens = list(shlex.shlex(prefix.replace("\n", ";"), posix=True, punctuation_chars=True))
    except ValueError:
        return cwd  # an opened quote hides what it holds, so the cd stays read from CWD
    here, words = cwd, []
    for token in tokens:
        if not set(token) <= set("&|;()"):  # a word, or a redirect such as `2>&1`, which holds `>`
            words.append(token)
            continue
        target = next((word for word in words[1:] if not word.startswith("-")), None)
        if token not in ("&&", ";", "("):
            here = cwd
        elif words[:1] in (["cd"], ["pushd"]) and target:
            here = os.path.normpath(os.path.join(here, os.path.expanduser(target)))
        words = []
    return here


def live_change_directory(command, cwd):
    """(folder, worktree, command): the folder of the live checkout a `cd` in COMMAND enters from the worktree CWD, the worktree, and COMMAND written
    without that cd, None when it cannot be; None for any other cd; a cd, never a write, is matched, since a script run after it may write anywhere."""
    root, inside, rest = (cwd or "").partition(WORKTREES)
    worktree = root + WORKTREES + rest.split("/")[0]
    for found in CHANGE_DIRECTORY.finditer(inert_text(command)) if inside else ():  # a cd inside a quote, heredoc or comment runs nothing
        path = os.path.normpath(os.path.join(directory_before(blanked_bodies(command[:found.start(1)]), cwd), os.path.expanduser(command[found.start(1):found.end(1)].strip("\"'"))))
        if (path + "/").startswith(root + "/") and WORKTREES not in path + "/":
            return path, worktree, without_change_directory(command, found, path, worktree)
    return None


def placed(value, folder, worktree):
    """(argument, changed): the argument VALUE as the rewrite writes it, FOLDER's absolute path when FOLDER holds it; None when WORKTREE alone holds it, since
    the rewrite would then read another file."""
    if value and os.path.exists(os.path.join(worktree, value)) and not os.path.exists(os.path.join(folder, value)):
        return None
    if value and os.path.exists(os.path.join(folder, value)):
        return shlex.quote(os.path.normpath(os.path.join(folder, value))), True
    return value, False


def inside_checkout(path, worktree):
    """Whether PATH, with its `..` and links resolved, lies in the live checkout WORKTREE belongs to, outside its worktrees."""
    real, root = os.path.realpath(path), os.path.realpath(worktree.split(WORKTREES)[0])
    return (real + "/").startswith(root + "/") and WORKTREES not in real + "/"


def reads_github(values):
    """Whether the `gh` call of VALUES reads: a listed read, given the number or url it needs, or an `api` call with no method, field or body."""
    verbs = tuple(values[1:3])
    if verbs in GH_READS:
        return verbs not in GH_NEEDS_TARGET or bool(re.fullmatch(r"#?\d+|https?://\S+", (values[3:4] or [""])[0] or ""))
    return values[1:2] == ["api"] and values[2:3] != ["graphql"] and not API_WRITES.search(" ".join(value or "" for value in values)) \
        and not any(API_SHORT_WRITES.match(value or "") or (value or "").startswith("--method") for value in values[2:])


def outside_single_quotes(word):
    """WORD without its single-quoted spans, where an apostrophe inside double quotes quotes nothing."""
    kept, quote, escaped = "", "", False
    for char in word:
        if quote == "'":
            quote = "" if char == "'" else quote
        elif escaped:
            kept, escaped = kept + char, False
        elif char == "\\":
            kept, escaped = kept + char, True
        elif quote == '"':
            kept, quote = kept + char, "" if char == '"' else quote
        elif char in "'\"":
            quote = char
            kept += char if char == '"' else ""
        else:
            kept += char
    return kept


def runs_program(value):
    """Whether VALUE, a git short option bundle, holds `O` before a letter that takes the rest of the bundle as its value."""
    if not re.fullmatch(r"-[^-].*", value):
        return False
    for char in value[1:]:
        if char == "O":
            return True
        if char in GIT_VALUE_LETTERS:
            return False
    return False


def stage_words(rest, blanked, start, stop):
    """[(written, value)] of the words of the simple command at START..STOP of REST, cut in BLANKED so a quoted space ends no word: the word as typed and
    its text without quotes, None for a redirect to a descriptor or /dev/null; None when a word expands, redirects to a file or cannot be read."""
    words = []
    for found in re.finditer(r"\S+", blanked[start:stop]):
        written = rest[start + found.start():start + found.end()]
        if PASSED_REDIRECT.fullmatch(found[0]):
            words.append((written, None))
            continue
        try:
            value, = shlex.split(written)
        except ValueError:
            return None
        if re.search(r"[<>$`*?\\\[#(){}]", found[0]) or re.search(r"[$`]|~[+-]", outside_single_quotes(written)):
            return None
        words.append((written, value))
    return words


def rewrite_stage(words, joint, folder, worktree):
    """The WORDS of one simple command written for the shell's own folder, None unless it is a read whose rewrite is certain to read the same thing."""
    written, values = [text for text, _ in words], [value for _, value in words]
    name = values[0]
    valued = {at + 1 for at, value in enumerate(values) if value and value.startswith("-") and not value.startswith("--") and value[-1] in TAKES_VALUE.get(name, "")}
    given = [at for at, value in enumerate(values) if at and value is not None and not value.startswith("-") and at not in valued]
    if name == "git":
        if values[1:2] and values[1] not in READ_GIT or any(runs_program(value or "") or (value or "").startswith("--") and len(value) > 2 and any(word.startswith(value[2:].split("=")[0]) for word in GIT_LONG_WRITES) for value in values[1:]):
            return None
        return written[:1] + ["-C", shlex.quote(folder)] + written[1:]
    if name == "gh" and reads_github(values) or name in NO_FILES:
        return written
    arguments = []  # the operands of a script, which stay as typed
    if "/" in name and not os.path.isabs(name) and os.path.isfile(os.path.join(folder, name)) and inside_checkout(os.path.join(folder, name), worktree):  # a script run by its relative path, which is no program of the system
        targets, arguments = [0], given
    elif name in SCRIPT_RUNNERS:
        if not given or any(value is not None and not re.fullmatch(r"-[IuBES]+", value) for value in values[1:given[0]]) or not os.path.isfile(os.path.join(folder, values[given[0]])) or not inside_checkout(os.path.join(folder, values[given[0]]), worktree):
            return None  # code fed on stdin or by a device is no script of the folder
        targets, arguments = given[:1], given[1:]
    elif name in READ_ONLY and all(re.fullmatch(rf"-(?!-)[{READ_ONLY[name]}0-9,\-]+", value) for value in values[1:] if value and value.startswith("-")) \
            and (name != "sed" or given and (SED_READ.fullmatch(values[given[0]]) or SED_ADDRESSED.fullmatch(values[given[0]])) and "\\" not in values[given[0]]):
        targets = [] if name in STDIN_ONLY else given[name in PATTERN_FIRST:]
        if name == "grep" and not targets and any(re.match(r"-[A-Za-z]*[rR]", value or "") for value in values[1:]):
            return None  # a recursive search with no path searches the folder it stands in
    else:
        return None
    if any(os.path.exists(os.path.join(folder, values[at])) for at in arguments):
        return None  # a script's argument may or may not be a path, and the rewrite cannot tell
    moved = []
    for at in targets:
        if (put := placed(values[at], folder, worktree)) is None:
            return None
        written[at] = put[0] if put[1] else written[at]
        moved += [at] if put[1] else []
    if prints_names(name, values, moved, len(targets), folder, bool(given)):
        return None  # the rewrite would print the absolute path where the cd call printed the name it was given
    if name in DEFAULT_FOLDER and not given:
        return written + [shlex.quote(folder)]
    return written if targets or joint == "|" else None  # with no file operand a command may read stdin or search the folder it stands in


def prints_names(name, values, moved, operands, folder, has_operand):
    """Whether the read NAME, given VALUES whose operands at MOVED the rewrite makes absolute, prints the name of an operand: always for NAME_PRINTERS and a
    folder's own listing, with an option of NAME_OPTIONS, with two operands, with a directory searched, or with a file listed."""
    if name in NAME_PRINTERS:
        return bool(moved) or name in DEFAULT_FOLDER and not has_operand
    options = "".join(value[1:] for value in values[1:] if value and value.startswith("-") and not value.startswith("--"))
    return (moved and operands > 1 or any(letter in options for letter in NAME_OPTIONS.get(name, ""))
            or name in ("grep", "rg") and any(os.path.isdir(os.path.join(folder, values[at])) for at in moved)
            or name == "ls" and any(os.path.isfile(os.path.join(folder, values[at])) for at in moved)) and name in NAME_OPTIONS


def free_of_comments(text):
    """Whether TEXT, read left to right with its quotes, holds no comment and no quote left open."""
    quote, escaped = "", False
    for at, char in enumerate(text):
        if escaped:
            escaped = False
        elif char == "\\" and quote != "'":
            escaped = True
        elif quote:
            quote = "" if char == quote else quote
        elif char in "'\"":
            quote = char
        elif char == "#" and (at == 0 or text[at - 1] in " \t\n;&|("):
            return False
    return not quote


def without_change_directory(command, found, folder, worktree):
    """COMMAND with the cd FOUND into FOLDER dropped and each later command written for the shell's own folder, `git -C FOLDER` for git and the absolute path
    for each argument naming something in FOLDER; None unless every command is a read whose rewrite is certain to read the same thing: a write, a second cd, an
    option that may take or write a file, a redirect to a file, expansion, glob, comment, code on stdin or in an option, or a name that
    also exists in WORKTREE keeps the refusal's plain message. A script run by an interpreter counts as a read: run by its absolute path it is no more than
    the hook already lets through."""
    rest = command[found.end():]
    if command[:found.start()].strip() or not free_of_comments(rest):
        return None  # a comment hides its lines from the reading, and an opened quote in it hides the next ones
    blanked = blank_text(rest)
    tail = ")" if blanked.rstrip().endswith(")") else ""
    if tail:
        rest, blanked = rest.rstrip()[:-1], blanked.rstrip()[:-1]
    stages, begin, joint = [], 0, ""
    for match in [*STAGE_JOINT.finditer(blanked), None]:
        stages.append((joint, begin, match.start() if match else len(blanked)))
        joint, begin = (match[0], match.end()) if match else ("", 0)
    if blanked[stages[0][1]:stages[0][2]].strip():
        return None  # something sits between the cd and its joint
    stages = stages[1:]
    if stages and not blanked[stages[-1][1]:stages[-1][2]].strip() and stages[-1][0] in (";", "\n"):
        stages.pop()
    if not stages or stages[0][0] not in ("&&", ";", "\n") or any(not blanked[a:b].strip() or joint == "&" for joint, a, b in stages):
        return None
    delimiter = re.match(r"[;&|({]|then|do", found[0])
    rewritten = []
    for at, (joint, begin, end) in enumerate(stages):
        words = stage_words(rest, blanked, begin, end)
        if words and [value for _, value in words][:1] == ["cd"] and len(words) == 2 and (words[1][1] or " ")[0] in "/~" and rewritten:
            moved = os.path.normpath(os.path.expanduser(words[1][1]))
            if joint != "&&" or inside_checkout(moved, worktree):
                return None  # a failed cd leaves the rest where the rewrite cannot, and a cd into the live checkout is refused again
            for later_joint, later_begin, later_end in stages[at + 1:]:  # what runs there must be a read too
                later = stage_words(rest, blanked, later_begin, later_end)
                if not later or later[0][1] is None or not rewrite_stage(later, later_joint, moved, moved):
                    return None
            return command[:found.start()] + (delimiter[0] + " " if delimiter else "") + "".join(rewritten) + " " + rest[begin - len(joint):] + tail  # an absolute cd sets the folder its rest runs in
        if not words or words[0][1] is None or not (stage := rewrite_stage(words, joint, folder, worktree)):
            return None
        rewritten.append((f" {JOINTS[joint]} " if rewritten else "") + " ".join(stage))
    return command[:found.start()] + (delimiter[0] + " " if delimiter else "") + "".join(rewritten) + tail


def unseen(lines, session_id):
    """LINES not yet reminded in this session, recorded so each playbook line is added to the context once; a record that cannot be read or written
    leaves them all unseen, since a reminder must never break the call it decorates."""
    if not session_id:
        return lines
    seen_file = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "teamwork-reminded" / f"{session_id}.txt"
    try:
        seen = set(seen_file.read_text().splitlines()) if seen_file.exists() else set()
        new = [line for line in lines if line not in seen]
        if new:
            seen_file.parent.mkdir(parents=True, exist_ok=True)
            with seen_file.open("a") as fh:
                fh.write("".join(line + "\n" for line in new))
        return new
    except OSError:
        return lines


def reminder(call, role, session_id=None):
    needles = REMINDED.get(call["write"], ())
    found = [f"- {path.relative_to(PLAYBOOKS.parents[1])}:{number}: {line.strip()}"
             for path in (PLAYBOOKS / "protocol.md", PLAYBOOKS / f"{role}.md", GRAMMAR)
             for number, line in enumerate(path.read_text().splitlines(), 1) if any(needle in line for needle in needles)]
    found = unseen(found, session_id)
    return found and "\n".join([f"Reminder: the playbook rules this `{call['called']}` must keep:", *found])


def command_of(event):
    return (event.get("tool_input") or {}).get("command", "")


def route(kind, event, role, me, listed):
    if kind == "SessionStart":
        gaps = (team_gaps.manager_actions(me, listed) if role == "manager" else team_gaps.worker_goal(me)) or []
        text = "\n".join([f"You are {me['name']}, a teamwork {role}: follow {PLAYBOOKS / (role + '.md')}.", *gaps])
        return {"hookSpecificOutput": {"hookEventName": kind, "additionalContext": text}}
    # once, so a real wait still stops; never while a subagent or a background command it waits on still runs
    if kind == "Stop" and role == "worker" and not event.get("stop_hook_active") and not background_work.running_work(event.get("transcript_path") or ""):
        goal = [line for line in team_gaps.worker_goal(me) if line.endswith(": open")]
        return goal and {"decision": "block", "reason": "\n".join(["Your goal still waits on you:", *goal,
                         "Take its next step; stop again only while a subagent, a check or your manager has it."])}
    entered = role == "worker" and live_change_directory(command_of(event), event.get("cwd"))
    if entered:  # guards the checkout every session loads
        again = (f"run this instead: `{entered[2]}`, which runs in your worktree, so a script that reads its working folder sees that one and a name it prints starts with the live folder's path"
                 if entered[2] else "run it again without that cd and read the live checkout by path or git -C")
        return {"hookSpecificOutput": {"hookEventName": kind, "permissionDecision": "deny", "permissionDecisionReason":
                f"This cd enters {entered[0]} in the live checkout, which every session loads, so an edit there lands outside your worktree; "
                f"nothing in this command ran; {again}, since your shell already stands in {entered[1]}."}}
    if kind == "PreToolUse" and writes_github_issue(command_of(event)):
        return {"hookSpecificOutput": {"hookEventName": kind, "permissionDecision": "deny", "permissionDecisionReason":
                f"Team work (a task, finding, hand-over, question or answer) lives on the git-refs board, never in a GitHub issue; nothing in this command ran. Write it with "
                f"`{PLAYBOOKS.parent / 'scripts' / 'use-board.py'}` with `file`, `comment`, `decide`, `edit` or `resolve`, as {PLAYBOOKS / 'adapters' / 'board.md'} says. When the owner asked for a GitHub issue, "
                "ask them to run the command themselves by typing `! <command>`."}}
    call = board.command(command_of(event))
    text = call and reminder(call, role, event.get("session_id"))
    return text and {"hookSpecificOutput": {"hookEventName": kind, "additionalContext": text}}


def main(args):
    event = json.load(sys.stdin)
    kind = event.get("hook_event_name")
    command = command_of(event)
    # without its host's command no session has a name, so no role matches and the role's SessionStart text never comes to say why
    if kind == "SessionStart" and (missing := next(filter(None, map(install_line.missing, session.NEEDS)), None)):
        print(json.dumps({"systemMessage": missing}))
    elif kind in ("SessionStart", "Stop") \
            or kind == "PreToolUse" and (board.command(command) or writes_github_issue(command) or live_change_directory(command, event.get("cwd"))):  # skip other Bash fast
        listed, me = session.sessions(event.get("session_id"))
        role = team_names.role(me.get("name"))
        if out := role and route(kind, event, role, me, listed):
            print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

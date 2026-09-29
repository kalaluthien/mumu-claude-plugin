"""Which checkerwork skills a change fits, read from a changed file's path and the text written to it.

  test  a code file (.py .sh .js .ts .kt ...) outside a test folder or test_* name
  spec  an `.als` file, or written text stating a protocol rule (never, always, only after, at most, ...)
  eval  a prompt of a Claude plugin: SKILL.md, skills/**/references/*.md, agents/*.md, commands/*.md,
        evals/**, CLAUDE.md, AGENTS.md
Files in a temp dir, a scratchpad or `~/.claude/projects` (memory) are not a change.
"""
import collections
import re

SKILLS = ("test", "spec", "eval")
CODE = re.compile(r"\.(py|sh|bash|zsh|js|mjs|cjs|ts|tsx|jsx|kt|kts|java|swift|rs|go|rb|c|cc|cpp|h)$")
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]*$|_test\.[a-z]+$|\.test\.[a-z]+$")
RULE = re.compile(r"\b(never|always|only after|at most|at least once|lifecycle|transition|permission|ownership|protocol)\b", re.I)
PROMPT = re.compile(r"(^|/)(SKILL\.md|CLAUDE\.md|AGENTS\.md)$|/skills/.+/references/[^/]+\.md$|/(agents|commands)/[^/]+\.md$|/evals/")
NOT_CHANGE = re.compile(r"^(/tmp/|/private/|/var/folders/)|/scratchpad/|/\.claude/projects/")
CALL = re.compile(r"checkerwork:(test|spec|eval)\b")
COMMIT = re.compile(r"(^|[;&|(]\s*|\s)git(\s+-C\s+(\S+))?\s+commit\b")


def fits(path, text):
    """The skills whose description a write of `text` to `path` fits; `path` is absolute or starts with /."""
    if not path or NOT_CHANGE.search(path):
        return set()
    out = set()
    if CODE.search(path) and not TEST_PATH.search(path):
        out.add("test")
    if path.endswith(".als") or RULE.search(text or ""):
        out.add("spec")
    if PROMPT.search(path):
        out.add("eval")
    return out


def added(diff):
    """{"/" + path: added lines joined} from a unified diff's text, a file with none added included."""
    files, path = collections.defaultdict(list), None
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            path = "/" + line.split(" b/", 1)[-1]
            files[path]
        elif path and line.startswith("+") and not line.startswith("+++"):
            files[path].append(line[1:])
    return {p: "\n".join(t) for p, t in files.items()}

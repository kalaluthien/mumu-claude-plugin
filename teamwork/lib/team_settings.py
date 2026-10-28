"""A repository's teamwork settings, read from `.teamwork/settings.json` at the git root of a folder, and the `Warning:` lines about them.

Keys, all optional: `refuse` (an issue rule refuses when true, else only warns), `title_max`, `backlog_label`, `scope_prefix`, and `tools_off`
(role to list of tools). No file, or a file that is no JSON object, gives every default; a key of the wrong type gives its default and a warning."""
import json
import pathlib

import agent

FILE = pathlib.Path(".teamwork", "settings.json")
DEFAULTS = {"refuse": False, "title_max": 40, "backlog_label": "backlog", "scope_prefix": "scope:",
            "tools_off": {role: tools.split(",") for role, tools in agent.TOOLS_OFF.items()}}
NUMBER = lambda value: isinstance(value, (int, float)) and not isinstance(value, bool)  # True is an int in Python, and no limit
TOOL_LISTS = lambda value: isinstance(value, dict) and all(isinstance(tools, list) and all(isinstance(tool, str) for tool in tools) for tools in value.values())
KINDS = {"refuse": ("a boolean", lambda value: isinstance(value, bool)), "title_max": ("a number", NUMBER),
         "backlog_label": ("a string", lambda value: isinstance(value, str)), "scope_prefix": ("a string", lambda value: isinstance(value, str)),
         "tools_off": ("an object of role to list of tool names", TOOL_LISTS)}


def root(folder):
    """The git root holding FOLDER, by its `.git` entry, which a worktree has as a file; None outside a repository."""
    here = pathlib.Path(folder).resolve()
    return next((candidate for candidate in (here, *here.parents) if (candidate / ".git").exists()), None)


def load(folder):
    """The settings of FOLDER's repository, every key filled, with `warnings`: the `Warning:` lines about the file to print."""
    top = root(folder)
    try:
        given = json.loads((top / FILE).read_text()) if top else {}
    except FileNotFoundError:
        given = {}
    except (OSError, ValueError):
        given = None
    if not isinstance(given, dict):
        return {**DEFAULTS, "warnings": [f"Warning: {FILE} is no JSON object, so every issue rule only warns and every key takes its default."]}
    out, warnings = dict(DEFAULTS), []
    for key, (kind, ok) in KINDS.items():
        if key not in given:
            continue
        if ok(given[key]):
            out[key] = {**DEFAULTS[key], **given[key]} if key == "tools_off" else given[key]
        else:
            warnings.append(f"Warning: `{key}` in {FILE} is not {kind}, so its default {json.dumps(DEFAULTS[key])} applies.")
    return {**out, "warnings": warnings}


def warning(text):
    """The `Warning:` line for an issue rule TEXT that only warns, naming where it is made a refusal."""
    return f"Warning: {text} This only warns, since {FILE} at the repository's git root does not set `\"refuse\": true`, which refuses it."

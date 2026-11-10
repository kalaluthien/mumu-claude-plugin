#!/usr/bin/env python3
"""Check every tracked file: Python compiles, manifests parse, Markdown links resolve, each plugin's manifest names its folder and the marketplace lists it, each hook, monitor and module path a manifest names exists, a command's file executable, each skill or `.github` script answers an unknown flag with exit 2, `usage:` on stderr and nothing on stdout, no plugin file, function or import is unreached, no plugin file names another plugin's file or skill, no skill file sits outside the skill folder hierarchy, no plugin holds a change its `version` does not cover, no script a plugin replays takes an unknown option as data, and every fixture runner passes: each `replay-*.py` or `replay-*.ts` directly in a `fixtures/` folder, and each `scripts/` script whose usage lists a `fixtures` call, run with it.

usage: check-repository.py [--skip-fixtures] [root]   (--skip-fixtures: no fixture runner, for a runner that checks a copy)

Prints one failure per line as `<kind> <path>: <detail>`, `unreached` lines being list-unreached.py's, `shared` lines
list-cross-plugin-names.py's, `unreleased` lines list-unreleased.py's and `misplaced` lines list-misplaced-references.py's, `option` lines a plugin's `fixtures/replay-option-calls.py`'s, and `fixture <path>: exit <n>, <last line>` a runner's that failed, then a summary line, and exits 0 only when nothing failed. Standard library only, Python 3.9.
"""

import concurrent.futures
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from urllib.parse import unquote

ROOT = pathlib.Path(__file__).resolve().parents[1]

MANIFEST_NAMES = {"plugin.json", "hooks.json", "monitors.json"}
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
INLINE_CODE = re.compile(r"(`+)(?:(?!\1).)+?\1")
INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(\s*([^)\s]+)(?:\s+[\"'(][^)]*)?\)")
REFERENCE_LINK = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(\S+)")
COMMAND_PATH = re.compile(r'^"\$\{CLAUDE_PLUGIN_ROOT\}"/(\S+)')
UNKNOWN_FLAG = "--no-such-flag"
ROOT_PATH = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)")
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
PLACEHOLDER = set("<*{")
OPTION_REPLAY = "replay-option-calls.py"  # a plugin keeps beside its scripts the replay that calls each with an unknown option
OPTION_SUMMARY = re.compile(r"^\d+ scripts, \d+ calls, \d+ not refused$", re.M)
RUNNER = re.compile(r"(?:^|/)fixtures/replay-[^/]+\.(?:py|ts)$")
FIXTURES_CALL = re.compile(r"^(?:usage:)? *\S+\.py fixtures\b", re.M)  # a skill script that checks the fixtures beside it
RUNNER_SECONDS = 1200
STAND_IN = "#!/bin/sh\necho 'a fixture runner may not start a live session' >&2\nexit 1\n"
LISTERS = (  # each lister's script, the failure lines it prints and its summary line; without the summary a lister that printed nothing would pass
    ("list-unreached.py", "unreached ", re.compile(r"^\d+ files, \d+ unreached$", re.M)),
    ("list-cross-plugin-names.py", "shared ", re.compile(r"^\d+ files, \d+ naming another plugin$", re.M)),
    ("list-unreleased.py", "unreleased ", re.compile(r"^\d+ plugins, \d+ unreleased$", re.M)),
    ("list-misplaced-references.py", "misplaced ", re.compile(r"^\d+ skill files, \d+ misplaced$", re.M)),
)


def list_files(root):
    """Tracked files when root is a git top level, otherwise every file under it."""
    try:
        top = subprocess.run(
            ["git", "-C", root, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        if os.path.realpath(top) == os.path.realpath(root):
            listing = subprocess.run(
                ["git", "-C", root, "ls-files", "-z"],
                capture_output=True, text=True, check=True,
            ).stdout
            return sorted(path for path in listing.split("\0") if path)
    except (OSError, subprocess.CalledProcessError):
        pass
    files = []
    for folder, subfolders, names in os.walk(root):
        subfolders[:] = [name for name in subfolders if name != ".git"]
        for name in names:
            files.append(os.path.relpath(os.path.join(folder, name), root))
    return sorted(name.replace(os.sep, "/") for name in files)


def is_manifest(path):
    name = path.rsplit("/", 1)[-1]
    return path == ".claude-plugin/marketplace.json" or name in MANIFEST_NAMES


def plugin_root(root, path):
    """The nearest folder above path that holds .claude-plugin/plugin.json."""
    parts = path.split("/")[:-1]
    while parts:
        if os.path.isfile(os.path.join(root, *parts, ".claude-plugin", "plugin.json")):
            return os.path.join(root, *parts)
        parts.pop()
    return None


def markdown_targets(text):
    """Link targets outside fenced and inline code."""
    fence = None
    for line in text.splitlines():
        mark = FENCE.match(line)
        if fence:
            if mark and mark.group(1)[0] == fence[0] and len(mark.group(1)) >= len(fence):
                fence = None
            continue
        if mark:
            fence = mark.group(1)
            continue
        line = INLINE_CODE.sub("", line)
        for match in INLINE_LINK.finditer(line):
            yield match.group(1)
        reference = REFERENCE_LINK.match(line)
        if reference:
            yield reference.group(1)


def check_markdown(root, path, text, failures):
    """Return the number of links and root paths checked in one file."""
    checked = 0
    folder = os.path.dirname(os.path.join(root, path))
    for target in markdown_targets(text):
        target = target.strip("<>")
        if SCHEME.match(target) or target.startswith("#") or PLACEHOLDER & set(target):
            continue
        local = unquote(target.split("#", 1)[0].split("?", 1)[0])
        if not local:
            continue
        checked += 1
        base = root if local.startswith("/") else folder
        if not os.path.exists(os.path.join(base, local.lstrip("/"))):
            failures.append("link {}: {} does not resolve".format(path, target))
    # A root path is a command or file the skill runs, usually inside code, so code is not skipped.
    for match in ROOT_PATH.finditer(text):
        relative = match.group(1).rstrip(".")
        if PLACEHOLDER & set(relative):
            continue
        checked += 1
        plugin = plugin_root(root, path)
        if plugin is None:
            failures.append("root-path {}: no plugin holds this file".format(path))
        elif not os.path.exists(os.path.join(plugin, relative)):
            failures.append("root-path {}: ${{CLAUDE_PLUGIN_ROOT}}/{} does not exist".format(path, relative))
    return checked


def manifest_paths(name, data):
    """[(path, is_command)] a hooks.json or monitors.json names, the path as written; a TypeError when its shape is not the one Claude Code reads."""
    if name == "monitors.json":
        expect(isinstance(data, list) and all(isinstance(monitor, dict) for monitor in data))
        found = [(monitor.get("command", ""), True) for monitor in data]
    else:
        expect(isinstance(data, dict) and set(data) <= {"description", "hooks", "modules"})
        events, modules = data.get("hooks", {}), data.get("modules", [])
        expect(isinstance(events, dict) and isinstance(modules, list) and all(isinstance(entries, list) for entries in events.values()))
        entries = [entry for listed in events.values() for entry in listed]
        expect(all(isinstance(entry, dict) and isinstance(entry.get("hooks"), list) for entry in entries))
        hooks = [hook for entry in entries for hook in entry["hooks"]]
        expect(all(isinstance(hook, dict) and isinstance(hook.get("type"), str) for hook in hooks))
        found = [(hook.get("command", ""), True) for hook in hooks if hook["type"] == "command"] + [(module, False) for module in modules]
    expect(all(isinstance(path, str) for path, _ in found))
    return found


def expect(holds):
    """A TypeError, which read_shaped names as a wrong shape, unless HOLDS."""
    if not holds:
        raise TypeError("a shape Claude Code does not read")


def string(value):
    """VALUE when it is a string, else a TypeError, which read_shaped names as a wrong shape."""
    if not isinstance(value, str):
        raise TypeError("no string")
    return value


def climbs_out(depth, written):
    """Whether WRITTEN, read from a folder DEPTH levels inside its plugin, steps above the plugin folder at any segment."""
    for segment in written.split("/"):
        depth += -1 if segment == ".." else 0 if segment in ("", ".") else 1
        if depth < 0:
            return True
    return False


def read_shaped(root, path, read, failures):
    """READ applied to the JSON at PATH; None when it does not parse, which the manifest parse names, or, with a line naming PATH, when its shape is not one READ takes."""
    try:
        with open(os.path.join(root, path), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    try:
        return read(data)
    except (AttributeError, TypeError, KeyError):
        failures.append("manifest {}: its shape is not the one Claude Code reads".format(path))
        return None


def check_plugins(root, files, failures):
    """Fail each plugin whose manifest names another folder or the marketplace leaves out, and each hook, monitor or module path that
    names no listed file in its plugin, or a command file that cannot run; returns how many paths it checked."""
    marketplace = ".claude-plugin/marketplace.json"
    # a local plugin's source is a "./<folder>" string; an external one's is an object, which names no folder here
    listed = read_shaped(root, marketplace, lambda data: {(plugin.get("name"), plugin.get("source")) for plugin in data["plugins"]
                                                          if isinstance(plugin.get("source"), str)}, failures)
    if listed is None and not os.path.isfile(os.path.join(root, marketplace)):
        listed = set()
    tracked, checked = set(files), 0
    for path in files:
        parts = path.split("/")
        if parts[1:] == [".claude-plugin", "plugin.json"]:
            name = read_shaped(root, path, lambda data: string(data["name"]), failures)
            if name is None:
                continue
            if name != parts[0]:
                failures.append("manifest {}: name {!r} is not its folder {!r}".format(path, name, parts[0]))
            # a marketplace that does not parse or has the wrong shape is named once already, so it fails no plugin again
            if listed is not None and (parts[0], "./" + parts[0]) not in listed:
                failures.append("manifest {}: lists no plugin {!r} with source ./{}".format(marketplace, parts[0], parts[0]))
        elif len(parts) == 3 and parts[1:] in (["hooks", "hooks.json"], ["monitors", "monitors.json"]):
            for written, is_command in read_shaped(root, path, lambda data: manifest_paths(parts[2], data), failures) or []:
                checked += 1
                command = COMMAND_PATH.match(written)
                if is_command and not command:
                    failures.append('hook {}: command {!r} is not "${{CLAUDE_PLUGIN_ROOT}}"/<path>'.format(path, written))
                    continue
                # matched against the listed names, since a case-insensitive disk finds a path whose case differs and a case-sensitive one does not,
                # and walked on disk as written, since normpath drops a trailing slash or a "x/.." the OS walks and refuses
                joined = os.path.join(parts[0], command.group(1)) if is_command else os.path.join(parts[0], parts[1], written)
                target = os.path.normpath(joined)
                if climbs_out(0 if is_command else 1, command.group(1) if is_command else written):
                    failures.append("hook {}: {} leaves its plugin folder, which an installed plugin holds alone".format(path, written))
                elif target not in tracked or not os.path.isfile(os.path.join(root, joined)):
                    failures.append("hook {}: {} names no file".format(path, written))
                elif is_command and not os.access(os.path.join(root, target), os.X_OK):
                    failures.append("hook {}: {} is not executable".format(target, written))
    return checked


def check_scripts(root, files, failures):
    """Call each skill and `.github` script with an unknown flag from an empty folder and fail each that does not answer it with exit 2,
    `usage:` on stderr and nothing on stdout; returns how many it called."""
    scripts = [path for path in files if path.endswith(".py")
               and (path.count("/") == 1 and path.startswith(".github/") or "/skills/" in path and path.split("/")[-2] == "scripts")]
    with tempfile.TemporaryDirectory() as empty:
        environment = {"PATH": os.environ.get("PATH", ""), "HOME": empty, "PYTHONDONTWRITEBYTECODE": "1"}  # a call leaves no __pycache__ in a root with no .gitignore
        for path in scripts:
            try:
                called = subprocess.run([sys.executable, os.path.join(root, path), UNKNOWN_FLAG], cwd=empty, env=environment,
                                        stdin=subprocess.DEVNULL, capture_output=True, text=True, errors="replace", timeout=30)
                answer = "exit {}, stdout {!r}".format(called.returncode, called.stdout[:80])
                wrong = called.returncode != 2 or "usage:" not in called.stderr or called.stdout
            except subprocess.TimeoutExpired:
                answer, wrong = "no answer in 30 s", True
            if wrong:
                failures.append("usage {}: {} gave {}; print the docstring on stderr and exit 2".format(path, UNKNOWN_FLAG, answer))
    return len(scripts)


def run_fixtures(root, files, failures):
    """Run each fixture runner from ROOT, four at a time, with stand-in `claude` and `herdr` first on PATH so none starts a live session, and
    fail each that exits non-zero or runs past RUNNER_SECONDS; returns how many ran."""
    calls = []
    for path in files:
        if RUNNER.search(path) and not path.endswith("/" + OPTION_REPLAY):
            calls.append((path, ["bun", path] if path.endswith(".ts") else [sys.executable, path]))
        elif re.search(r"(?:^|/)scripts/[^/]+\.py$", path):
            with open(os.path.join(root, path), encoding="utf-8", errors="replace") as handle:
                if FIXTURES_CALL.search(handle.read()):
                    calls.append((path, [sys.executable, path, "fixtures"]))
    with tempfile.TemporaryDirectory() as stand_ins:
        for name in ("claude", "herdr"):
            with open(os.path.join(stand_ins, name), "w") as handle:
                handle.write(STAND_IN)
            os.chmod(os.path.join(stand_ins, name), 0o755)
        environment = {**os.environ, "PATH": stand_ins + os.pathsep + os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"}

        def run(call):
            path, argv = call
            try:
                done = subprocess.run(argv, cwd=root, env=environment, stdin=subprocess.DEVNULL, capture_output=True, text=True, errors="replace", timeout=RUNNER_SECONDS)
            except (OSError, subprocess.TimeoutExpired) as error:
                return "fixture {}: {}".format(path, error)
            last = ((done.stdout.strip() or done.stderr.strip()).splitlines() or [""])[-1][:200]
            return "fixture {}: exit {}, {}".format(path, done.returncode, last) if done.returncode else None

        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            failures += [line for line in pool.map(run, calls) if line]
    return len(calls)


def main(args):
    skip_fixtures = args[:1] == ["--skip-fixtures"]
    args = args[1:] if skip_fixtures else args
    if len(args) > 1 or (args and args[0].startswith("-")):
        print(__doc__, file=sys.stderr)
        return 2
    root = os.path.abspath(args[0] if args else ROOT)
    if not os.path.isdir(root):
        print(__doc__, file=sys.stderr)
        return 2
    failures = []
    compiled = manifests = links = docs = 0
    files = list_files(root)
    for path in files:
        full = os.path.join(root, path)
        if not os.path.isfile(full):
            continue
        if path.endswith(".py"):
            compiled += 1
            try:
                with open(full, "rb") as handle:
                    compile(handle.read(), path, "exec", dont_inherit=True)
            except (SyntaxError, ValueError) as error:
                failures.append("compile {}: {}".format(path, error))
        elif path.endswith(".json") and is_manifest(path):
            manifests += 1
            try:
                with open(full, encoding="utf-8") as handle:
                    json.load(handle)
            except (ValueError, UnicodeDecodeError) as error:
                failures.append("json {}: {}".format(path, error))
        elif path.endswith(".md"):
            docs += 1
            with open(full, encoding="utf-8", errors="replace") as handle:
                links += check_markdown(root, path, handle.read(), failures)
    paths = check_plugins(root, files, failures)
    scripts = check_scripts(root, files, failures)
    replays = [(path, "option ", OPTION_SUMMARY) for path in files if path.endswith("/fixtures/" + OPTION_REPLAY)]
    for script, kind, summary in [(str(pathlib.Path(__file__).with_name(name)), kind, summary) for name, kind, summary in LISTERS] + [(os.path.join(root, path), kind, summary) for path, kind, summary in replays]:
        # no bytecode, since list-cross-plugin-names.py loads list-unreached.py and a replay imports its plugin's modules, which would leave __pycache__ in a checked root
        listed = subprocess.run([sys.executable, script, root], capture_output=True, text=True, errors="replace", env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        if listed.returncode or not summary.search(listed.stdout):
            lines = [line for line in listed.stdout.splitlines() if line.startswith(kind)]
            failures += lines or ["{}{}: exit {}, no summary line: {}".format(kind, os.path.basename(script), listed.returncode, listed.stderr.strip())]
    runners = 0 if skip_fixtures else run_fixtures(root, files, failures)
    for line in failures:
        print(line)
    counts = "{} py compiled, {} manifests parsed, {} hook paths found, {} scripts called, {} fixture runners passed, {} links in {} md resolved, {} failures".format(
        compiled, manifests, paths, scripts, runners - sum(line.startswith("fixture ") for line in failures), links, docs, len(failures))
    print(("FAIL: " if failures else "ok: ") + counts)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

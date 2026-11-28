#!/usr/bin/env python3
"""Check every tracked file: Python compiles, manifests parse, Markdown links resolve, each plugin's manifest names its folder and the marketplace lists it, each hook, monitor and module path a manifest names exists, a command's file executable, each skill or `.github` script answers an unknown flag with exit 2, `usage:` on stderr and nothing on stdout, and `--help` with exit 0, `usage:` on stdout and nothing on stderr, no plugin file, function or import is unreached, no plugin file names another plugin's file or skill or is a symlink resolving outside its plugin, no skill file sits outside the skill folder hierarchy, no plugin file name or environment variable it reads breaks its kind's form, no plugin holds a change its `version` does not cover, no script a plugin replays takes an unknown option as data, and every fixture runner passes: each `replay-*.py` or `replay-*.ts` directly in a `fixtures/` folder, each run with no argument, each `scripts/` script whose usage lists a `fixtures` call, run with it, and each step a skill script lists by a `steps` call in its usage, one per line, run as its own call with that step's word and replayed while its skill's folder and its plugin's `lib/` stay the same, four at a time with stand-in `claude` and `herdr` first on PATH so none starts a live session. A `fixtures/replay-option-calls.py` calls each script of its part with `--help` and an unknown option at each word position and must exit 0 and print a summary line.

usage: check-repository.py [--skip-fixtures] [--fresh [runner]...] [root]   (--skip-fixtures: no fixture runner, for a runner that checks a copy; --fresh: run each runner named, or every runner when none is named, even when it passed on the same files; a runner is its path from root, or its path and step, as a `fixture` line prints it)

Prints one failure per line as `<kind> <path>: <detail>`, `unreached` lines being list-unreached.py's, `shared` lines
list-cross-plugin-names.py's, `unreleased` lines list-unreleased.py's and `misplaced` lines list-misplaced-references.py's, `misnamed` lines list-misnamed.py's, `option` lines a plugin's `fixtures/replay-option-calls.py`'s, and `fixture <path>: exit <n>, <last line>` a runner's that failed, each of its other `FAIL` lines indented beneath, then a summary line, and exits 0 only when nothing failed. A fixture runner that passed on the same files, its plugin's folder, `.github/`, `.claude-plugin/` and the root files (every file for one in `.github/` or whose source names `.github`), is not run again by any session of the repository, which the summary counts as replayed; a failed runner always runs. Standard library only, Python 3.9.
"""

import concurrent.futures
import hashlib
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
OPTION_SUMMARY = re.compile(r"^\d+ scripts, \d+ calls, \d+ not answered$", re.M)
RUNNER = re.compile(r"(?:^|/)fixtures/replay-[^/]+\.(?:py|ts)$")
FIXTURES_CALL = re.compile(r"^(?:usage:)? *\S+\.py fixtures\b", re.M)  # a skill script that checks the fixtures beside it
STEPS_CALL = re.compile(r"^(?://|#)? *usage: *\S+ steps\b", re.M)  # a skill script whose steps run one by one, each on its skill's files
INTERPRETERS = {".py": [sys.executable], ".ts": ["bun"], ".cjs": ["node"], ".js": ["node"]}
RUNNER_SECONDS = 1200
STAND_IN = "#!/bin/sh\necho 'a fixture runner may not start a live session' >&2\nexit 1\n"
LISTERS = (  # each lister's script, the failure lines it prints and its summary line; without the summary a lister that printed nothing would pass
    ("list-unreached.py", "unreached ", re.compile(r"^\d+ files, \d+ unreached$", re.M)),
    ("list-cross-plugin-names.py", "shared ", re.compile(r"^\d+ files, \d+ naming another plugin$", re.M)),
    ("list-unreleased.py", "unreleased ", re.compile(r"^\d+ plugins, \d+ unreleased$", re.M)),
    ("list-misplaced-references.py", "misplaced ", re.compile(r"^\d+ skill files, \d+ misplaced$", re.M)),
    ("list-misnamed.py", "misnamed ", re.compile(r"^\d+ files, \d+ misnamed$", re.M)),
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
    """Call each skill and `.github` script from an empty folder with an unknown flag and with `--help`, and fail each that does not answer
    the first with exit 2, `usage:` on stderr and nothing on stdout, and the second with exit 0, `usage:` on stdout and nothing on stderr;
    returns how many it called."""
    scripts = [path for path in files if path.endswith(".py")
               and (path.count("/") == 1 and path.startswith(".github/") or "/skills/" in path and path.split("/")[-2] == "scripts")]
    with tempfile.TemporaryDirectory() as empty:
        environment = {"PATH": os.environ.get("PATH", ""), "HOME": empty, "PYTHONDONTWRITEBYTECODE": "1"}  # a call leaves no __pycache__ in a root with no .gitignore
        for path in scripts:
            for flag, code, said, silent, rule in ((UNKNOWN_FLAG, 2, "stderr", "stdout", "print the docstring on stderr and exit 2"),
                                                   ("--help", 0, "stdout", "stderr", "print the docstring on stdout and exit 0")):
                try:
                    called = subprocess.run([sys.executable, os.path.join(root, path), flag], cwd=empty, env=environment,
                                            stdin=subprocess.DEVNULL, capture_output=True, text=True, errors="replace", timeout=30)
                    answer = "exit {}, {} {!r}".format(called.returncode, silent, getattr(called, silent)[:80])
                    wrong = called.returncode != code or "usage:" not in getattr(called, said) or getattr(called, silent)
                except subprocess.TimeoutExpired:
                    answer, wrong = "no answer in 30 s", True
                if wrong:
                    failures.append("usage {}: {} gave {}; {}".format(path, flag, answer, rule))
    return len(scripts)


def files_digest(root, files, folders, with_root_files):
    """A sha-256 of the path and bytes of each file of FILES under one of FOLDERS, or at the root of ROOT when WITH_ROOT_FILES, in order."""
    digest = hashlib.sha256()
    for path in files:
        if any(path.startswith(folder) for folder in folders) or (with_root_files and "/" not in path):
            try:
                with open(os.path.join(root, path), "rb") as handle:
                    digest.update(path.encode() + b"\0" + handle.read() + b"\0")
            except OSError:
                digest.update(path.encode() + b"\0missing\0")
    return digest.hexdigest()


def passes_folder(root):
    """The folder in the git common dir that keeps one marker per runner pass, or None when ROOT is no git checkout."""
    common = subprocess.run(["git", "-C", root, "rev-parse", "--path-format=absolute", "--git-common-dir"], capture_output=True, text=True)
    return pathlib.Path(common.stdout.strip(), "check-repository-passes") if common.returncode == 0 and common.stdout.strip() else None


def runner_marker(root, files, folder, path, argv, step=False):
    """The marker file of a pass of runner PATH on its files: those of its plugin's folder, `.github/`, `.claude-plugin/` and the root, or all of them for a runner of `.github/` or one whose source names `.github`, since it reads other plugins; for one STEP of a skill script, those of its skill's folder and its plugin's `lib/`, since a step reads only them, so a change elsewhere in its plugin replays it."""
    with open(os.path.join(root, path), encoding="utf-8", errors="replace") as handle:
        wide = not step and (path.startswith(".github/") or ".github" in handle.read())
    parts = path.split("/")
    folders = ("/".join(parts[:3]) + "/", parts[0] + "/lib/") if step else ("",) if wide else (parts[0] + "/", ".github/", ".claude-plugin/")
    digest = hashlib.sha256("\0".join([files_digest(root, files, folders, not wide and not step), *argv]).encode()).hexdigest()[:32]
    return folder / digest


def runner_steps(root, path, environment):
    """The calls of each step skill script PATH lists by its `steps` call, one per line, or a failure line when it lists none."""
    interpreter = INTERPRETERS[os.path.splitext(path)[1]]
    try:
        listed = subprocess.run([*interpreter, path, "steps"], cwd=root, env=environment, stdin=subprocess.DEVNULL, capture_output=True, text=True, errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired) as error:
        return [], "fixture {} steps: {}".format(path, error)
    steps = listed.stdout.split()
    if listed.returncode or not steps:
        return [], "fixture {} steps: exit {}, no step listed".format(path, listed.returncode)
    return [(path, [*interpreter, path, step], step) for step in steps], None


def run_fixtures(root, files, failures, fresh):
    """Run each fixture runner from ROOT, four at a time, with stand-in `claude` and `herdr` first on PATH so none starts a live session, and
    fail each that exits non-zero or runs past RUNNER_SECONDS, each step a skill script lists as its own runner, unless it passed on the same files before, unless FRESH is True (every runner) or holds its path; returns (how many, how many replayed)."""
    calls, stepped = [], []
    for path in files:
        if RUNNER.search(path) and not path.endswith("/" + OPTION_REPLAY):
            calls.append((path, ["bun", path] if path.endswith(".ts") else [sys.executable, path], None))
        elif re.search(r"(?:^|/)skills/[^/]+/scripts/[^/]+$", path) and os.path.splitext(path)[1] in INTERPRETERS:
            with open(os.path.join(root, path), encoding="utf-8", errors="replace") as handle:
                source = handle.read()
            if FIXTURES_CALL.search(source):
                calls.append((path, [*INTERPRETERS[os.path.splitext(path)[1]], path, "fixtures"], None))
            if STEPS_CALL.search(source):
                stepped.append(path)
    with tempfile.TemporaryDirectory() as stand_ins:
        for name in ("claude", "herdr"):
            with open(os.path.join(stand_ins, name), "w") as handle:
                handle.write(STAND_IN)
            os.chmod(os.path.join(stand_ins, name), 0o755)
        environment = {**os.environ, "PATH": stand_ins + os.pathsep + os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"}
        for path in stepped:
            listed, failure = runner_steps(root, path, environment)
            calls += listed
            failures += [failure] if failure else []

        folder = passes_folder(root)
        replayed = []
        # a runner reads the folder as it is, so a file not yet added counts
        untracked = subprocess.run(["git", "-C", root, "ls-files", "-z", "--others", "--exclude-standard"], capture_output=True, text=True).stdout.split("\0")
        readable = sorted({*files, *(path for path in untracked if path)})

        def run(call):
            path, argv, step = call
            label = path + " " + step if step else path
            marker = runner_marker(root, readable, folder, path, argv, bool(step)) if folder else None
            if marker and not (fresh is True or path in fresh or label in fresh) and marker.exists():
                replayed.append(path)
                return None
            try:
                done = subprocess.run(argv, cwd=root, env=environment, stdin=subprocess.DEVNULL, capture_output=True, text=True, errors="replace", timeout=RUNNER_SECONDS)
            except (OSError, subprocess.TimeoutExpired) as error:
                return "fixture {}: {}".format(label, error)
            lines = (done.stdout.strip() or done.stderr.strip()).splitlines() or [""]
            # a runner's last line is only its verdict, so the lines naming each fault go with it, for a reader of the CI log
            faults = ["    " + line[:200] for line in lines[:-1] if line.startswith("FAIL")]
            if done.returncode:
                return "\n".join(["fixture {}: exit {}, {}".format(label, done.returncode, lines[-1][:200])] + faults)
            if marker:
                try:
                    folder.mkdir(parents=True, exist_ok=True)
                    marker.write_text(path + "\n")
                except OSError:
                    pass  # a git dir the run cannot write is no reason to lose the verdict
            return None

        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            failures += [line for line in pool.map(run, calls) if line]
    return len(calls), len(replayed)


def main(args):
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    skip_fixtures, fresh, named = False, set(), False
    while args[:1] in (["--skip-fixtures"], ["--fresh"]):
        skip_fixtures, named = skip_fixtures or args[0] == "--skip-fixtures", named or args[0] == "--fresh"
        args = args[1:]
        while named and args and not args[0].startswith("-") and not os.path.isdir(args[0]):
            fresh.add(args[0])
            args = args[1:]
    if named and not fresh:
        fresh = True
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
    runners, replayed = (0, 0) if skip_fixtures else run_fixtures(root, files, failures, fresh)
    for line in failures:
        print(line)
    counts = "{} py compiled, {} manifests parsed, {} hook paths found, {} scripts called, {} fixture runners passed ({} replayed), {} links in {} md resolved, {} failures".format(
        compiled, manifests, paths, scripts, runners - sum(line.startswith("fixture ") for line in failures), replayed, links, docs, len(failures))
    print(("FAIL: " if failures else "ok: ") + counts)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Check every tracked file: Python compiles, manifests parse, Markdown links resolve.

Usage: check-repository.py [root]

Prints one failure per line as `<kind> <path>: <detail>`, then a summary line,
and exits 0 only when nothing failed. Standard library only, Python 3.9.
"""

import json
import os
import re
import subprocess
import sys
from urllib.parse import unquote

# Copies of docs kept with dangling links on purpose, as page-check fixtures.
BROKEN_ON_PURPOSE = {
    "paperwork/skills/zoom/references/ui/fixtures/formats-missing-row.md",
    "paperwork/skills/zoom/references/ui/fixtures/mermaid-false-kept.md",
    "paperwork/skills/zoom/references/ui/fixtures/mermaid-missing-row.md",
}

MANIFEST_NAMES = {"plugin.json", "hooks.json", "monitors.json"}
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
INLINE_CODE = re.compile(r"(`+)(?:(?!\1).)+?\1")
INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(\s*([^)\s]+)(?:\s+[\"'(][^)]*)?\)")
REFERENCE_LINK = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(\S+)")
ROOT_PATH = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)")
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
PLACEHOLDER = set("<*{")


def list_files(root):
    """Tracked files when root is a git top level, otherwise every file under it."""
    try:
        top = subprocess.run(
            ["git", "-C", root, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        if os.path.realpath(top) == os.path.realpath(root):
            out = subprocess.run(
                ["git", "-C", root, "ls-files", "-z"],
                capture_output=True, text=True, check=True,
            ).stdout
            return sorted(p for p in out.split("\0") if p)
    except (OSError, subprocess.CalledProcessError):
        pass
    files = []
    for folder, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in names:
            files.append(os.path.relpath(os.path.join(folder, name), root))
    return sorted(f.replace(os.sep, "/") for f in files)


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
        ref = REFERENCE_LINK.match(line)
        if ref:
            yield ref.group(1)


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
        rel = match.group(1).rstrip(".")
        if PLACEHOLDER & set(rel):
            continue
        checked += 1
        plugin = plugin_root(root, path)
        if plugin is None:
            failures.append("root-path {}: no plugin holds this file".format(path))
        elif not os.path.exists(os.path.join(plugin, rel)):
            failures.append("root-path {}: ${{CLAUDE_PLUGIN_ROOT}}/{} does not exist".format(path, rel))
    return checked


def main():
    default = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else default)
    failures = []
    compiled = manifests = links = docs = 0
    for path in list_files(root):
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
        elif path.endswith(".md") and path not in BROKEN_ON_PURPOSE:
            docs += 1
            with open(full, encoding="utf-8", errors="replace") as handle:
                links += check_markdown(root, path, handle.read(), failures)
    for line in failures:
        print(line)
    counts = "{} py compiled, {} manifests parsed, {} links in {} md resolved, {} failures".format(
        compiled, manifests, links, docs, len(failures))
    print(("FAIL: " if failures else "ok: ") + counts)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

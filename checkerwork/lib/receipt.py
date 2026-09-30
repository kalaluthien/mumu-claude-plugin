"""The receipt of an Alloy model, stored under a key of what the model reads.

The key is the model's path and content and the path and content of each `spec/` file it opens, transitively. An `open`
naming no file under `spec/` (`util/ordering`) is outside the key. Receipts live under the repository's common git dir,
so every worktree shares them; only `receipt.json` is kept.
"""
import hashlib
import json
import os
import re
import subprocess
import tempfile

MODEL = re.compile(r"(?m)^[ \t]*(check|run)[ \t{]")
OPEN = re.compile(r"(?m)^[ \t]*(?:private[ \t]+)?open[ \t]+([\w./$-]+)")


def is_model(text):
    return bool(MODEL.search(text))


def model_key(model, read):
    """`read(path)` gives a file's text, or None when there is none; paths are relative to the repo root, with `/`."""
    seen, todo = {}, [os.path.normpath(model)]
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        text = read(path)
        seen[path] = text
        for name in OPEN.findall(text or ""):
            dep = os.path.normpath(os.path.join(os.path.dirname(path), name + ".als"))
            if dep.startswith("spec/") and read(dep) is not None:
                todo.append(dep)
    h = hashlib.sha256()
    for path in sorted(seen):
        h.update(f"{path}\0{hashlib.sha256((seen[path] or '').encode()).hexdigest()}\0".encode())
    return h.hexdigest()


def read_file(path):
    try:
        with open(path, errors="ignore") as f:
            return f.read()
    except OSError:
        return None


def store_dir():
    """The receipt folder, or None outside a git repository."""
    p = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], capture_output=True, text=True)
    return os.path.join(p.stdout.strip(), "spec-receipts") if p.returncode == 0 and p.stdout.strip() else None


def valid(text):
    try:
        return isinstance(json.loads(text).get("commands"), dict)
    except (TypeError, ValueError, AttributeError):
        return False


def load(store, key):
    """The stored receipt's text, or None when absent or not a JSON receipt."""
    text = read_file(os.path.join(store, key, "receipt.json"))
    return text if valid(text) else None


def save(store, key, text):
    folder = os.path.join(store, key)
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder)
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.replace(tmp, os.path.join(folder, "receipt.json"))

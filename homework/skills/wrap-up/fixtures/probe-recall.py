#!/usr/bin/env python3
"""Build a backed-up memory folder and the tidies a dream could leave of it, run restore-lessons.py on each, and print one
line per step and `probe: <passed> of <steps> steps pass`; exit 0 only when all pass.

usage: probe-recall.py"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
RESTORE = str(HERE.parent / "scripts/restore-lessons.py")
INDEX = """# Memory index

- [Release tags](release-tags.md) — you pick a plugin version to release, since git tags are shared across plugins
- [Shell traps](shell-traps.md) — you write a zsh redirect or a sed sweep
"""
LESSONS = {"release-tags.md": "Pick the next free tag across every plugin.\n", "shell-traps.md": "Quote each glob.\n"}
CORRECTION = {"id": "s1-0", "quote": "태그가 겹쳐", "what_went_wrong": "the agent tagged a plugin release with a version another plugin's tags already used"}
results = []


def step(name, ok, detail=""):
    results.append(bool(ok))
    print(f"{'pass' if ok else 'FAIL'}: {name}" + ("" if ok else f" ({detail})"))


def build(root, tidy):
    """A memory folder at root/home, its backup at its path below /, and the tidy applied to the live folder."""
    home = root / "home"
    home.mkdir(parents=True)
    (home / "MEMORY.md").write_text(INDEX)
    for name, text in LESSONS.items():
        (home / name).write_text(text)
    backup = root / "backup/day"
    shutil.copytree(home, backup / str(home).lstrip("/"))
    (root / "dejavu").mkdir()
    (root / "dejavu/friction.jsonl").write_text(json.dumps(CORRECTION) + "\n")
    tidy(home)
    return home, backup


def snapshot(folder):
    return {path.name: path.read_text() for path in sorted(folder.glob("*.md"))}


def run(root, backup):
    return subprocess.run([sys.executable, RESTORE, str(backup), str(root / "dejavu")], capture_output=True, text=True)


def drop_release(home):
    (home / "release-tags.md").unlink()
    (home / "MEMORY.md").write_text("\n".join(line for line in INDEX.splitlines() if "release-tags" not in line) + "\n")


def narrow_release(home):
    (home / "MEMORY.md").write_text(INDEX.replace("[Release tags](release-tags.md) — you pick a plugin version to release, since git "
                                                  "tags are shared across plugins", "[Numbers](release-tags.md) — you pick a number"))
    (home / "release-tags.md").write_text("Pick a number.\n")


def drop_shell(home):
    (home / "shell-traps.md").unlink()
    (home / "MEMORY.md").write_text("\n".join(line for line in INDEX.splitlines() if "shell-traps" not in line) + "\n")


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="probe-recall-") as folder:
        root = pathlib.Path(folder)
        for name, tidy in (("a tidy that deletes the one lesson a correction needs", drop_release),
                           ("a tidy that narrows that lesson's index line past the correction", narrow_release)):
            home, backup = build(root / tidy.__name__, tidy)
            done = run(root / tidy.__name__, backup)
            step(f"{name} gets the lesson and its index line back",
                 done.returncode == 0 and snapshot(home) == {"MEMORY.md": snapshot(home)["MEMORY.md"], **LESSONS}
                 and INDEX.splitlines()[2] in snapshot(home)["MEMORY.md"].splitlines()
                 and "restored " in done.stdout and "for s1-0" in done.stdout, done.stdout + done.stderr)
            after = snapshot(home)
            again = run(root / tidy.__name__, backup)
            step(f"{name}: a second run changes nothing", snapshot(home) == after and "0 lessons restored" in again.stdout, again.stdout)
        home, backup = build(root / "drop_shell", drop_shell)
        tidied = snapshot(home)
        done = run(root / "drop_shell", backup)
        step("a tidy that keeps the needed lesson and drops an unneeded one changes nothing",
             done.returncode == 0 and snapshot(home) == tidied and "0 lessons restored for 1 corrections" in done.stdout, done.stdout)
        step("the output names every correction and the tidy's diff",
             "correction s1-0:" in done.stdout and "-- [Shell traps](shell-traps.md)" in done.stdout, done.stdout)
        empty = root / "no-backup"
        (empty / "dejavu").mkdir(parents=True)
        done = run(empty, empty / "backup/day")
        step("with no backup it changes nothing and says so", done.returncode == 0 and done.stdout.startswith("no backup at"), done.stdout)
    print(f"probe: {sum(results)} of {len(results)} steps pass")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

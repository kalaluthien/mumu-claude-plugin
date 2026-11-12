#!/usr/bin/env python3
"""Print `PASS` when every playbook part of kick-off is named for the role that reads it and every script sits beside the one part
that alone names it, else `FAIL: <what differed>`.

usage: replay-role-parts.py

A session follows the links of its own role's playbook, `references/<role>.md`, for each role the routing table of `SKILL.md`
names and for the judge the protocol briefs, and every role follows the links of `references/protocol.md`, which `SKILL.md`
routes to first. A part reached from one role's playbook alone, through no other playbook, is named `<role>-<part>.md`; a part
named `<role>-<part>.md` is reached from that role's playbook and not from `protocol.md`; every Markdown file under `references/` is
reached; and every link a reached file holds names a file that exists. A script that one Markdown file under `references/` alone
names, of every file of the plugin and `README.md` but the fixtures and kick-off's scripts, sits in that file's folder, the file's
path without `.md`, as `scripts/<script>`; every other script sits in kick-off's `scripts/`."""
import pathlib
import re
import subprocess
import sys

KICK_OFF = pathlib.Path(__file__).resolve().parents[1]
REFERENCES = KICK_OFF / "references"
ROOT = KICK_OFF.parents[2]
LINK = re.compile(r"\]\(([^)#\s]+\.md)(?:#[^)]*)?\)")


def links(path):
    return {(path.parent / target).resolve() for target in LINK.findall(path.read_text()) if "://" not in target}


def walk(starts, stops):
    seen, todo = set(), list(starts)
    while todo:
        path = todo.pop()
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        todo += [target for target in links(path) if target not in stops and REFERENCES in target.parents]
    return seen


def broken(paths):
    return sorted(f"{path.relative_to(REFERENCES.parent)} links {target.relative_to(REFERENCES.parent)}, which does not exist"
                  for path in paths for target in links(path) if KICK_OFF in target.parents and not target.exists())


def misplaced_scripts():
    listed = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-co", "--exclude-standard", "teamwork", "README.md"], capture_output=True, text=True)
    names = listed.stdout.split() if listed.returncode == 0 and listed.stdout else [
        str(path.relative_to(ROOT)) for path in [*(ROOT / "teamwork").rglob("*"), ROOT / "README.md"] if "__pycache__" not in path.parts]
    files = [ROOT / name for name in names if (ROOT / name).is_file()]
    scripts = [path for path in files if path.suffix == ".py" and path.parent.name == "scripts" and KICK_OFF in path.parents]
    readers = [path for path in files if "fixtures" not in path.parts and path not in scripts]
    texts = {path: path.read_text(errors="replace") for path in readers}
    problems = []
    for script in scripts:
        namers = [path for path, text in texts.items() if script.name in text]
        alone = namers[0] if len(namers) == 1 and namers[0].suffix == ".md" and REFERENCES in namers[0].parents else None
        home = alone.with_suffix("") / "scripts" if alone else KICK_OFF / "scripts"
        if script.parent != home:
            problems.append(f"{script.relative_to(KICK_OFF)} belongs in {home.relative_to(KICK_OFF)}/, since "
                            + (f"{alone.relative_to(KICK_OFF)} alone names it" if alone else "no one part alone names it"))
    return problems


def roles():
    rows = [line.split("|") for line in (KICK_OFF / "SKILL.md").read_text().splitlines() if line.startswith("| `")]
    named = {row[2].strip(): set() for row in rows if len(row) > 3}
    for row in rows:
        named[row[2].strip()] |= {(KICK_OFF / target).resolve() for target in LINK.findall(row[3])}
    if "/judge.md" in (REFERENCES / "protocol.md").read_text():
        named["judge"] = set()
    return {role: starts | {(REFERENCES / f"{role}.md").resolve()} for role, starts in named.items()}


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    starts = roles()
    playbooks = {(REFERENCES / f"{role}.md").resolve() for role in starts} | {(REFERENCES / "protocol.md").resolve()}
    shared = walk([(REFERENCES / "protocol.md").resolve()], playbooks - {(REFERENCES / "protocol.md").resolve()})
    readers = {}
    for role, paths in starts.items():
        for path in walk(paths, playbooks - {(REFERENCES / f"{role}.md").resolve()}):
            readers.setdefault(path, set()).add(role)
    problems = []
    for path in sorted(path.resolve() for path in REFERENCES.rglob("*.md")):
        name, owners = str(path.relative_to(REFERENCES)), readers.get(path, set())
        prefix = path.name.split("-")[0] if path.parent == REFERENCES.resolve() and "-" in path.name else None
        if path in playbooks:
            continue
        if path not in shared and not owners:
            problems.append(f"{name} is reached by no role")
        elif path not in shared and len(owners) == 1 and prefix != next(iter(owners)):
            problems.append(f"{name} is read by the {next(iter(owners))} alone but not named {next(iter(owners))}-<part>.md")
        if prefix in starts and prefix not in owners:
            problems.append(f"{name} is named for the {prefix} but {prefix}.md does not reach it")
        if prefix in starts and path in shared:
            problems.append(f"{name} is named for the {prefix} but protocol.md, which every role reads, reaches it")
    problems += broken(set(readers) | shared | {(KICK_OFF / "SKILL.md").resolve()})
    problems += misplaced_scripts()
    print("PASS" if not problems else "FAIL: " + "; ".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

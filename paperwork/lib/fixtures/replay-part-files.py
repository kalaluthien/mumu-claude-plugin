#!/usr/bin/env python3
"""Replay a session that keeps each system example and a flow fixture as part files in git, edits one level, and builds again.

usage: replay-part-files.py

Each contract is split by `check-contract.py split` into an empty folder of a scratch git repository and built with no page named
by each way a name reaches it: a link to the folder, a link to a copy of the contract file reached through `..` from a folder or as
`a/../`, that copy reached through a link to a folder beside it then `..`, a link to the folder's `levels` then `..`, `..` run in its
`levels`, and `.` run in it; each writes the page beside the name given, or beside what the OS opens where the name ends in `..` or
passes a link then `..`, and nowhere else; the folder and its page are committed; then a text in the `info` of a record of the middle level, or of the next level holding one, a text no
other part reads, is changed in that level's part file alone and the page built again.
`git diff --name-only` must name only that part file and the page; the page's changed lines must be only lines each holding the
edited record alone, and that part's key; the folder, read back, must join to the contract it was split from, with the edit. Before
the edit, a split into the folder again is refused by name and writes nothing; `score-contract.py` and `sort-edges.py` print on a
system folder what they print on its file, which exits 0 or 1 with no traceback or usage; and a build and a check of a copy of the folder with a level's part file missing, a
level file `top.json` does not list, `levels` no list of ids, a part file that is no object, a list of records holding a text, or
a part file nested past Python's depth, are each refused by its own message naming that file, or the folder for the last, with no traceback and no page written; the contract with each list of records a
level holds that it lacks, or else the first, given empty splits into a folder that reads back to it.
It prints `PASS <contract>` or `FAIL <contract>: <reason>` per contract, then PASS or FAIL."""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

LIB = pathlib.Path(__file__).resolve().parents[1]
PLUGIN = LIB.parent
sys.path.insert(0, str(LIB))
from contract_parts import FLOW, SYSTEM, load  # noqa: E402

CONTRACTS = [("system", path) for path in sorted((PLUGIN / "skills/system/examples").glob("*/contract.json"))] + [
    ("flow", PLUGIN / "skills/flow/fixtures/name-lookup.json"), ("flow", PLUGIN / "skills/flow/fixtures/launch-plan.json")]
SHAPES = {"system": SYSTEM, "flow": FLOW}


def run(command, where=None):
    done = subprocess.run([str(part) for part in command], capture_output=True, text=True, cwd=where)
    return done.returncode, done.stdout + done.stderr


def git(repository, *args):
    return run(["git", "-C", repository, "-c", "user.name=replay", "-c", "user.email=replay@example.invalid", "-c", "commit.gpgsign=false", *args])


def changed_lines(repository, file):
    """The lines of FILE that the working tree removes or adds against the last commit."""
    _, diff = git(repository, "diff", "--unified=0", "--", file)
    return [line[1:] for line in diff.splitlines() if line[:1] in "+-" and not line.startswith(("+++", "---"))]


def record_id(line):
    """The id of the one record LINE holds alone, or None."""
    try:
        value = json.loads(line.strip().rstrip(","))
    except ValueError:
        return None
    return value.get("id") if isinstance(value, dict) else None


def broken(skill, folder, scratch):
    """Why a build or a check of FOLDER with one part file missing, one level file top.json does not list, `levels` no list, a part
    no object, a list of records holding a text or a part nested too deep, was not refused by its own message with no page written, or
    None."""
    make = PLUGIN / "skills" / skill / "scripts" / "make-page.py"
    first = sorted((folder / "levels").glob("*.json"))[0]
    held = json.loads(first.read_text())
    kind = next(kind for kind in SHAPES[skill]["held"] if held.get(kind))
    cases = (("missing", lambda copy: (copy / "levels" / first.name).unlink(), first.name),
             ("unlisted", lambda copy: shutil.copy(first, copy / "levels" / "unlisted.json"), "names no level top.json lists"),
             ("no list", lambda copy: (copy / "top.json").write_text(json.dumps({**json.loads((copy / "top.json").read_text()), "levels": "all"})),
              "`levels` must list the level ids"),
             ("no object", lambda copy: (copy / "levels" / first.name).write_text("[]"), f"{first.name}: a level's part is an object"),
             ("no record", lambda copy: (copy / "levels" / first.name).write_text(json.dumps({**held, kind: ["x"]})), f"{first.name}: a level's part is an object"),
             ("too deep", lambda copy: (copy / "levels" / first.name).write_text("[" * 100000 + "]" * 100000), str(scratch / "too-deep")))
    for name, change, named in cases:
        copy, page = scratch / name.replace(" ", "-"), scratch / f"{name.replace(' ', '-')}.html"
        shutil.copytree(folder, copy)
        change(copy)
        status, said = run([sys.executable, make, copy, page])
        checked = run([sys.executable, make.with_name("check-contract.py"), "check", copy, "--part", "top"])
        if status != 1 or named not in said or page.exists() or checked[0] != 1 or named not in checked[1] or "Traceback" in said + checked[1]:
            return f"a folder with {name} part was not refused by name: exit {status}, {said.strip()[:200]}"
    return None


def replay(skill, source, repository):
    scripts = PLUGIN / "skills" / skill / "scripts"
    folder, page = repository / "contract", repository / "page.html"
    folder.mkdir()
    status, said = run([sys.executable, scripts / "check-contract.py", "split", source, folder])
    if status:
        return f"split into an empty folder refused: {said.strip()}"
    beside = repository.parent / f"{repository.name}-paths"
    real, linked, nest, docs = (beside / name for name in ("real", "linked", "nest", "docs"))
    for made in (real / "sub", linked / "a", nest, docs):
        made.mkdir(parents=True)
    shutil.copy(source, real / "contract.json")
    (linked / "contract.json").symlink_to(real / "contract.json")
    (beside / "sub").symlink_to(real / "sub")
    (nest / "levels").symlink_to(folder / "levels")
    (docs / "contract").symlink_to(folder)
    builds = (  # each way a name reaches the contract: run where, by what name, the page it must write, the pages it must not
        (docs, "contract", docs / "page.html", [page]),
        (linked / "a", "../contract.json", linked / "page.html", [real / "page.html", linked / "a" / "page.html"]),
        (linked, "a/../contract.json", linked / "page.html", [real / "page.html"]),
        (beside, "sub/../contract.json", real / "page.html", [beside / "page.html"]),
        (nest, "levels/..", page, [nest / "page.html", beside / "page.html"]),
        (folder / "levels", "..", page, [folder / "page.html", folder / "levels" / "page.html"]),
        (folder, ".", page, [folder / "page.html"]))
    for where, name, written, others in builds:
        for old in (written, *others):
            old.unlink(missing_ok=True)
        status, said = run([sys.executable, scripts / "make-page.py", name], where=where)
        if status or not written.is_file() or any(other.exists() for other in others):
            return f"`make-page.py {name}` run in {where}, with no page named, wrote no {written} alone: {said.strip()[:300]}"
    for args in (("init", "-q"), ("add", "."), ("commit", "-q", "-m", "split")):
        status, said = git(repository, *args)
        if status:
            return f"git {args[0]}: {said.strip()}"
    status, said = run([sys.executable, scripts / "check-contract.py", "split", source, folder])
    _, dirty = git(repository, "status", "--porcelain")
    if status != 1 or str(folder) not in said or dirty:
        return f"a split into a folder that holds files was not refused by name, or wrote: {said.strip()} {dirty.strip()}"
    if skill == "system":
        for script in ("score-contract.py", "sort-edges.py"):
            on_file, on_folder = (run([sys.executable, scripts / script, contract, "--root", PLUGIN.parent]) for contract in (source, folder))
            if on_file[0] not in (0, 1) or not on_file[1].strip() or "Traceback" in on_file[1] or "usage:" in on_file[1]:
                return f"{script} on the file did not run: exit {on_file[0]}, {on_file[1].strip()[:200]!r}"
            if on_file != on_folder:
                return f"{script} prints on the folder {on_folder[1][:200]!r}, on the file {on_file[1][:200]!r}"
    original = json.loads(source.read_text())
    empty = [kind for kind in SHAPES[skill]["held"] if kind not in original] or list(SHAPES[skill]["held"])[:1]
    emptied = {**original, **{kind: [] for kind in empty}}
    empty_source, empty_folder = repository.parent / f"{repository.name}-empty.json", repository.parent / f"{repository.name}-empty"
    empty_source.write_text(json.dumps(emptied, ensure_ascii=False))
    status, said = run([sys.executable, scripts / "check-contract.py", "split", empty_source, empty_folder])
    if status or load(empty_folder, SHAPES[skill]) != emptied:
        return f"a contract with empty lists of {', '.join(empty)} does not read back from its folder: {said.strip()[:200]}"
    refused = broken(skill, folder, repository.parent / f"{repository.name}-broken")
    if refused:
        return refused
    levels = json.loads((folder / "top.json").read_text())["levels"]
    for level in levels[len(levels) // 2:] + levels[:len(levels) // 2]:
        name, file = f"levels/{level}", folder / "levels" / f"{level}.json"
        part = json.loads(file.read_text())
        found = [(kind, record, key) for kind in ("edges", "nodes", "areas", "tasks", "milestones") for record in part.get(kind, [])
                 if isinstance(record, dict) and isinstance(record.get("info"), dict) for key, value in record["info"].items() if isinstance(value, str)]
        if found:
            break
    else:
        return "no level holds a record with a text in its info"
    kind, record, key = found[0]
    record["info"][key] += " Told again."
    file.write_text(json.dumps(part, ensure_ascii=False, indent=2) + "\n")
    status, said = run([sys.executable, scripts / "make-page.py", folder, page])
    if status or f"checked and built: {name}\n" not in said:
        return f"the build after an edit to {name} did not check and build it alone: {said.strip()[:300]}"
    _, names = git(repository, "diff", "--name-only")
    if sorted(names.split()) != sorted([f"contract/{name}.json", "page.html"]):
        return f"git diff names {names.split()}, not only contract/{name}.json and page.html"
    keyed = f'"{name}": '
    lines = changed_lines(repository, "page.html")
    stray = [line for line in lines if not line.lstrip().startswith(keyed) and record_id(line) != record["id"]]
    if stray or not any(json.dumps(record["info"][key], ensure_ascii=False)[1:-1] in line for line in lines):
        return f"the page's changed lines are not only those of `{record['id']}` and the key of {name}: {[line[:120] for line in stray[:3]]}"
    original = json.loads(source.read_text())
    for entry in original[kind]:
        if entry.get("id") == record["id"]:
            entry["info"][key] = record["info"][key]
    if load(folder, SHAPES[skill]) != original:
        return "the folder, read back, does not join to the contract it was split from with the edit"
    return None


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    failed = False
    with tempfile.TemporaryDirectory() as scratch:
        for k, (skill, source) in enumerate(CONTRACTS):
            label = f"{skill} {source.parent.name if source.name == 'contract.json' else source.stem}"
            repository = pathlib.Path(scratch) / str(k)
            repository.mkdir()
            reason = replay(skill, source, repository)
            print(f"FAIL {label}: {reason}" if reason else f"PASS {label}")
            failed |= bool(reason)
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

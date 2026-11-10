#!/usr/bin/env python3
"""Plant each way a plugin file can name another plugin on a throwaway copy of this repository, and print `ok <case>` or `FAIL <case>: <detail>` per case, then `PASS` as the last line when all hold, else `FAIL`.

usage: replay-cross-plugin-cases.py

Each case runs `.github/check-repository.py` on the copy, and requires it to fail naming the planted line or to pass."""

import itertools
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
MANIFEST = ".claude-plugin/plugin.json"


def copy_repository(target):
    """A copy of the tracked and untracked-but-not-ignored files of this repository in target."""
    out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=REPOSITORY, capture_output=True, text=True, check=True).stdout
    for path in filter(None, out.split("\0")):
        if (REPOSITORY / path).is_file():
            (target / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPOSITORY / path, target / path)


def run_check(base, appended):
    """The exit status and lines of the repository check on a copy with each text appended to its file."""
    with tempfile.TemporaryDirectory() as work:
        root = pathlib.Path(work)
        shutil.copytree(base, root, dirs_exist_ok=True)
        for path, text in appended.items():
            with open(root / path, "a") as handle:
                handle.write(text)
        result = subprocess.run([sys.executable, str(root / ".github" / "check-repository.py"), "--skip-fixtures", str(root)], capture_output=True, text=True)
        return result.returncode, result.stdout.splitlines()


def main(args):
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    holds = True
    with tempfile.TemporaryDirectory() as work:
        base = pathlib.Path(work)
        copy_repository(base)
        plugins = sorted(manifest.parent.parent.name for manifest in base.glob("*/" + MANIFEST))
        host = {plugin: sorted(path.relative_to(base).as_posix() for path in (base / plugin / "skills").glob("*/SKILL.md"))[0] for plugin in plugins}
        status, lines = run_check(base, {})
        good = status == 0
        print(("ok" if good else "FAIL") + " the check passes on the repository with nothing planted")
        holds = holds and good
        # name: (file appended to, appended text, line that must be printed or None when the check must pass)
        cases = {}
        for plugin, other in itertools.permutations(plugins, 2):
            cases["{} names a path of {}".format(plugin, other)] = (host[plugin], "\nsee ../{}/{}\n".format(other, MANIFEST), "shared {} names {}/{}".format(host[plugin], other, MANIFEST))
            skill = sorted(path.parent.name for path in (base / other / "skills").glob("*/SKILL.md"))[0]
            cases["{} names a skill of {}".format(plugin, other)] = (host[plugin], "\nrun {}:{}\n".format(other, skill), "shared {} names {}:{}".format(host[plugin], other, skill))
        sample = sorted(path.relative_to(base).as_posix() for path in base.glob("*/skills/*/examples/**/*.txt"))[0]
        other = [plugin for plugin in plugins if plugin != sample.split("/")[0]][0]
        cases["a sample under examples/ naming another plugin fails"] = (sample, "\nsee {}/{}\n".format(other, MANIFEST), "shared {} names {}/{}".format(sample, other, MANIFEST))
        cases["a bare file name of another plugin is no path"] = (host[plugins[0]], "\nsee plugin.json\n", None)
        for name, (path, text, wanted) in cases.items():
            status, lines = run_check(base, {path: text})
            problems = [] if status == (1 if wanted else 0) else ["exit {}".format(status)]
            problems += ["missing " + wanted] if wanted and wanted not in lines else []
            print("ok " + name if not problems else "FAIL {}: {}".format(name, "; ".join(problems)))
            holds = holds and not problems
    print("PASS" if holds else "FAIL")
    return 0 if holds else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

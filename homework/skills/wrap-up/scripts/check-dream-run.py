#!/usr/bin/env python3
"""Check what a dream run must not leave undone or unsafe, with no model call.

usage: check-dream-run.py facets <dejavu>
       check-dream-run.py memory <config> [<pool>...]

`facets` fails, exit 1, when a digest in <dejavu>/digests has no facet in <dejavu>/facets, or one that is not a JSON
object with `friction` and `habits` lists, printing `facets missing: <session>` per digest and a `facets: <n> of <m>` line.
`memory` scans the `.md` files of every memory folder `<config>` names (or only the pools named; with none named and no
`autoMemoryDirectory` in <config>/settings.json it exits 1 with a message naming the setting): it replaces each
credential value in place, keeping the credential's name, printing `redacted <file>:<line> <kind>`, and prints `injected
<file>:<line>` for each line that tells an agent to ignore its instructions or to send out secrets, which it leaves for the
owner to judge; it exits 1 when it printed either and ends with a `memory: <n> redacted, <m> injected` line."""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "lib"))
import credentials  # noqa: E402
import memory_home  # noqa: E402


def facets(dejavu):
    digests = sorted(path.stem for path in (pathlib.Path(dejavu) / "digests").glob("*.txt"))
    missing = []
    for session in digests:
        try:
            facet = json.loads((pathlib.Path(dejavu) / "facets" / f"{session}.json").read_text())
            whole = isinstance(facet, dict) and all(isinstance(facet.get(key), list) for key in ("friction", "habits"))
        except (OSError, ValueError):
            whole = False
        if not whole:
            missing.append(session)
    print("\n".join(f"facets missing: {session}" for session in missing))
    print(f"facets: {len(digests) - len(missing)} of {len(digests)}")
    return 1 if missing else 0


def memory(config, pools):
    redacted = injected = 0
    for pool in pools or memory_home.pools(config):
        for path in sorted(pathlib.Path(pool).glob("*.md")):
            text = path.read_text()
            clean, found = credentials.redact(text)
            if found:
                path.write_text(clean)
                print("\n".join(f"redacted {path}:{number} {kind}" for number, kind in found))
            redacted += len(found)
            lines = credentials.injected(clean)
            print("\n".join(f"injected {path}:{number}" for number in lines))
            injected += len(lines)
    print(f"memory: {redacted} redacted, {injected} injected")
    return 1 if redacted or injected else 0


def main(args):
    if len(args) == 2 and args[0] == "facets":
        return facets(args[1])
    if len(args) >= 2 and args[0] == "memory":
        return memory(args[1], args[2:])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

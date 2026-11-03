#!/usr/bin/env python3
"""Tell whether the owner manages each repository a fix would touch, by its origin's owner, before writing there.

usage: check-repository-owner.py <login> <root>...   one line per root: `own <root>` when its origin's owner is
                                                     <login> or it has no origin, else `foreign <root> <reason>`

A folder in no repository, or one its repository ignores, is foreign, since an installed plugin's copy may hold no
`.git` and sit inside the owner's config repository; memory folders are no repository and are never checked.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import memory_home  # noqa: E402

# https://host/owner/repo, git@host:owner/repo and ssh://git@host/owner/repo alike
OWNER = re.compile(r"^(?:[a-z+]+://)?(?:[^@/]+@)?[^/:]+[:/]([^/]+)/[^/]+?/?$")


def verdict(login, root):
    top = memory_home.git(root, "rev-parse", "--show-toplevel")
    if not top:
        return f"foreign {root} in no repository"
    # a clone kept inside the owner's repository but ignored by it, such as a plugin copy in the config folder, is not theirs
    if memory_home.git(top, "check-ignore", str(pathlib.Path(root).resolve())):
        return f"foreign {root} ignored by {top}"
    url = memory_home.git(root, "remote", "get-url", "origin")
    if not url:
        return f"own {root} with no origin"
    match = OWNER.match(url)
    owner = match.group(1) if match else None
    if owner and owner.lower() == login.lower():
        return f"own {root}"
    return f"foreign {root} origin {url}"


def main(args):
    if len(args) < 2 or any(arg.startswith("-") for arg in args):
        print(__doc__, file=sys.stderr)
        return 2
    login, roots = args[0], args[1:]
    lines = [verdict(login, root) for root in roots]
    for line in lines:
        print(line)
    foreign = sum(line.startswith("foreign ") for line in lines)
    print(f"{foreign} of {len(lines)} roots foreign: write nothing there and hand nothing over; find a way around it in "
          "what the owner manages, else write a patch in the plugin's data folder and show its path.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""List each plugin file that names a file or a skill of another plugin.

usage: list-cross-plugin-names.py [root]

A plugin is each folder of root (default: this repository) that holds `.claude-plugin/plugin.json`. A file names another plugin's
file when list-unreached.py's reference parsing, run over every plugin at once, finds a path in its text that ends a path of
that plugin and none of its own plugin; it names a skill when its text holds `<plugin>:<skill>` of another plugin.
Prints `shared <path> names <other path>` and `shared <path> names <plugin>:<skill>` lines, then a summary, and exits 1 when it
printed any of them, else 0. Standard library only, Python 3.9."""

import importlib.util
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

spec = importlib.util.spec_from_file_location("list_unreached", HERE / "list-unreached.py")
list_unreached = importlib.util.module_from_spec(spec)
spec.loader.exec_module(list_unreached)


def main(args):
    if len(args) > 1 or (args and args[0].startswith("-")):
        print(__doc__, file=sys.stderr)
        return 2
    root = pathlib.Path(args[0] if args else ROOT).resolve()
    if not root.is_dir():
        print(__doc__, file=sys.stderr)
        return 2
    plugins = [manifest.parent.parent for manifest in sorted(root.glob("*/.claude-plugin/plugin.json"))]
    texts = {}
    for plugin in plugins:
        for path in list_unreached.list_files(plugin):
            texts["{}/{}".format(plugin.name, path)] = list_unreached.read_text(plugin, path)
    skill_name = re.compile(r"\b({}):([a-z][\w-]*)".format("|".join(re.escape(plugin.name) for plugin in plugins) or "(?!)"))
    lines = []
    for path, targets in list_unreached.find_references(texts, across_plugins=True).items():
        lines += ["shared {} names {}".format(path, target) for target in sorted(targets) if target.split("/")[0] != path.split("/")[0]]
    for path, text in texts.items():
        for plugin, skill in sorted(set(skill_name.findall(text))):
            if plugin != path.split("/")[0] and (root / plugin / "skills" / skill).is_dir():
                lines.append("shared {} names {}:{}".format(path, plugin, skill))
    for line in sorted(lines):
        print(line)
    print("{} files, {} naming another plugin".format(len(texts), len(lines)))
    return 1 if lines else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

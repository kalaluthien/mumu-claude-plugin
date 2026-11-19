"""Unfold the contracts a fixtures folder keeps as changes to a whole contract beside them."""
import copy
import json


def copies(folder):
    """Each contract of FOLDER by name: each whole one, a JSON object in its own file, then each copy `contract-copies.json` holds
    under its base's name as a list of changes, `[path, value]` setting what the path leads to and `[path]` taking it out."""
    held = json.loads((folder / "contract-copies.json").read_text())
    for path in sorted(folder.glob("*.json")):
        whole = json.loads(path.read_text())
        if path.stem in held or isinstance(whole, dict) and path.stem != "contract-copies":
            yield path.stem, whole
        for name, changes in held.get(path.stem, {}).items():
            contract = copy.deepcopy(whole)
            for path_to, *value in changes:
                at = contract
                for key in path_to[:-1]:
                    at = at[key]
                if not value:
                    del at[path_to[-1]]
                elif path_to[-1] == len(at):
                    at.append(value[0])
                else:
                    at[path_to[-1]] = value[0]
            yield name, contract

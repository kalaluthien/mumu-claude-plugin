"""Names the install page of a command that is missing."""
import shutil

INSTALL = {"herdr": "https://herdr.dev"}


def missing(name):
    """The line that tells a person to install NAME when it is not on PATH, else None."""
    return None if shutil.which(name) else f"`{name}` is not installed: install it from {INSTALL[name]}"

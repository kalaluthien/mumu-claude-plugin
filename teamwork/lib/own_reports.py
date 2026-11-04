"""The urls of the reports a manager posted itself, which its heartbeat must not feed back to it as news."""
import data_folder


def _file():
    folder = data_folder.folder("own-reports")
    return folder and folder / "urls"


def note(url):
    """Records URL as posted by this project's manager; nothing outside a repository."""
    path = _file()
    if path and url:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as out:
            out.write(url.strip() + "\n")


def urls():
    path = _file()
    return set(path.read_text().split()) if path and path.exists() else set()

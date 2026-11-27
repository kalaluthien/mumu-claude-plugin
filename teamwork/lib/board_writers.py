"""The one gate of every board write and change close: who the writer is, taken from what started its session, never from a flag or a rename,
and the one table `MAY` of which role may write which kind of record.
- `writer()` the session running this process as `Writer(name, role, typed)`: the name it was started with, else the one `record` kept for its session id,
  its role by that name's form (None for a session in no team, such as the owner's own), and the prompts a person typed into it and the answers they picked in it
- `check(verb, number, fields, writer)` why WRITER may not do VERB (a board write verb, or `close`) on task or change NUMBER, whose record FIELDS
  holds (for a comment its `text` and fields, for a close the change); empty when it may
- `record(name)` keeps NAME as this session's name, raising ValueError when it would change the role it has"""
import collections
import json
import re

import agent
import claude_config
import team_names

Writer = collections.namedtuple("Writer", "name role typed")
ANY, OWN = "any", "own"  # OWN: only on a change whose branch the writer's name owns
TEAM = {"manager": ANY, "worker": ANY, None: ANY}
# kind of record -> {role: where it may write it}; None is a session in no team, such as the owner's own; a sentinel only reports
MAY = {"comment": {**TEAM, "sentinel": ANY},
       "decision": TEAM,
       "hold": TEAM,  # who holds a task, which `hold` sets with no decider named
       "owner decision": {"manager": ANY, "worker": ANY},  # the typed-words check, not the role, keeps it the owner's
       **{verb: TEAM for verb in ("file", "edit", "title", "resolve", "reopen", "label", "depend")},
       "close": {"manager": ANY, "worker": OWN}}
QUOTE = re.compile(r"^>(.*)$", re.M)


def folder():
    """Where `record` keeps each session's name, one file per session id, read only by `writer`."""
    return claude_config.folder() / "teamwork" / "session-names"


def recorded():
    session_id = agent.own_id()
    try:
        return json.loads((folder() / f"{session_id}.json").read_text()).get("name") if session_id else None
    except (OSError, ValueError, AttributeError):
        return None


def role(name):
    try:
        return team_names.parse(name).role
    except ValueError:
        return None


def writer():
    name = agent.started_name() or recorded()
    # a one-shot run is typed by the session that started it, never by a person
    return Writer(name, role(name), tuple(agent.typed(agent.own_transcript())) if agent.interactive() else ())


def record(name):
    had = writer().role
    if had and role(name) != had:
        raise ValueError(f"this session is a {had}, and {name} would make it {'a ' + role(name) if role(name) else 'one of no role'}; a session keeps the role it started with")
    session_id = agent.own_id()
    if session_id:
        folder().mkdir(parents=True, exist_ok=True)
        (folder() / f"{session_id}.json").write_text(json.dumps({"name": name}))


def kind(verb, fields):
    if "by" not in fields:
        return "hold" if "holders" in fields else verb
    return "owner decision" if fields["by"] == "owner" else "decision"


def flat(text):
    return " ".join(text.split())


def check(verb, number, fields, writer):
    found = []
    what = kind(verb, fields)
    where = MAY[what].get(writer.role)
    if where is None or where == OWN and not team_names.owns(writer.name, fields.get("headRefName", "")):
        allowed = ", ".join(f"{role or 'a session in no team'}{' on its own branch' * (at == OWN)}" for role, at in MAY[what].items())
        place = f"change {number}" if verb == "close" else f"#{number}" if number else "the board"
        found.append(f"{writer.name or 'this session'} ({writer.role or 'in no team'}) may not write {'an' if what[0] in 'aeiou' else 'a'} {what} on {place}: only {allowed} may")
    if what == "decision" and fields["by"] != writer.name:
        found.append(f"a decision is its writer's own, by {writer.name}, never by {fields['by']}")
    if what == "owner decision":
        prose = re.sub(r"^(`{3,}|~{3,}).*?^\1", "", fields.get("text", ""), flags=re.M | re.S)
        # each run of `>` lines is one quote, so a quote repeated or taken from two prompts or answers is still the owner's
        said = [quote for run in re.findall(r"(?:^>.*(?:\n|$))+", prose, re.M) if (quote := flat("\n".join(QUOTE.findall(run))))]
        if not said:
            found.append("a decision by the owner quotes the owner's words as its `>` lines: pass them by `--owner-said <file>`")
        elif not all(any(quote in flat(prompt) for prompt in writer.typed) for quote in said):
            found.append("the `>` lines are no words the owner typed or picked in this session; quote the owner's prompt as they typed it, or the answer they picked")
    return found

#!/usr/bin/env python3
"""Answer the tool prompt a session waits at with the choice of that number, only for a listed kind of prompt and never with
a choice that allows more than the one action asked; else print why and exit 1, leaving the prompt to the owner.

usage: answer-prompt.py <name> <choice>"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
import session  # noqa: E402

# A prompt's question starts with one of these: a Bash command, an edit, a file creation
LISTED = ("Do you want to proceed?", "Do you want to make this edit", "Do you want to create")
# A choice whose label says one of these grants later actions too, which no single answer may
WIDER = ("don't ask again", "always allow", "allow all", "during this session")
OPTION = re.compile(r"^\s*(?:[>❯›]\s*)?(\d+)\.\s+(.*\S)\s*$")


def prompt_on(screen):
    """The question and the numbered choices of the last prompt on the screen, or None when it shows none."""
    lines = screen.splitlines()
    starts = [i for i, line in enumerate(lines) if (m := OPTION.match(line)) and m.group(1) == "1"]
    if not starts:
        return None
    first = starts[-1]
    choices = {}
    for line in lines[first:]:
        if m := OPTION.match(line):
            choices[m.group(1)] = m.group(2)
        elif line.strip() and choices:
            break
    question = next((line.strip() for line in reversed(lines[:first]) if line.strip()), "")
    return question, choices


def main(args):
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    name, choice = args[0], args[1].strip()
    live = session.agent(name)
    if not live:
        sys.exit(f"answer-prompt.py: {name} is not live; nothing answered.")
    if live.get("agent_status") != "blocked":
        sys.exit(f"answer-prompt.py: {name} waits at no prompt (it is {live.get('agent_status')}); nothing answered.")
    found = prompt_on(session.screen(live["pane_id"]))
    if not found:
        sys.exit(f"answer-prompt.py: {name}'s screen shows no numbered choices; nothing answered.")
    question, choices = found
    if not question.startswith(LISTED):
        sys.exit(f"answer-prompt.py: \"{question}\" is not on the list of prompts a manager answers; `ask` the owner.")
    if choice not in choices:
        sys.exit(f"answer-prompt.py: {name}'s prompt has no choice {choice} (it has {', '.join(choices)}); nothing answered.")
    label = choices[choice]
    if any(w in label.lower().replace("’", "'") for w in WIDER):
        sys.exit(f"answer-prompt.py: choice {choice} \"{label}\" allows more than this one action, so it is never sent; `ask` the owner.")
    try:
        session.answer(live["pane_id"], choice)
    except RuntimeError as e:
        sys.exit(f"answer-prompt.py: {e}; nothing answered.")
    print(f"{name} answered \"{question}\" with {choice}. {label}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

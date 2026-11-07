"""Strip the `Judge note:` paragraph from a board text, so a worker builds to the criteria and not to the cases a judge tries against them."""
import re

# A note may open the text, follow `DECIDED: ` on the same line or be bold, since the manager writes the routing text by hand.
NOTE = re.compile(r"^(?:DECIDED: )?\**Judge note:\**.*?(?=\n\s*\n|\n```|\Z)\s*", re.M | re.S)


def without_judge_note(text):
    return NOTE.sub(lambda found: "DECIDED:\n\n" if found.group(0).startswith("DECIDED: ") else "", text)

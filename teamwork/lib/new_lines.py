"""Which of a monitor's lines are new: one printed stays quiet while it holds, and after a short gap in which it vanished."""

FORGET_POLLS = 5  # a status flips between polls, so a line gone for fewer polls than this is the same gap coming back


class NewLines:
    def __init__(self, forget=FORGET_POLLS):
        self.forget = forget
        self.absent = {}  # line -> polls since it was last in the lines, for each line printed and not yet forgotten

    def update(self, lines):
        """The lines to print for this poll's LINES, in order."""
        present = set(lines)
        fresh = [line for line in lines if line not in self.absent]
        self.absent = {k: 0 if k in present else polls + 1 for k, polls in self.absent.items() if k in present or polls + 1 < self.forget}
        self.absent.update({line: 0 for line in fresh})
        return fresh
